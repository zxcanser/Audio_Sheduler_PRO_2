import hashlib
import os
import tempfile
import threading
import time
from collections import deque
from typing import Callable, Deque, List, Optional

import tkinter as tk
import numpy as np
import soundfile as sf

from models import ClientCall
from services.playback_coordinator import PlaybackCoordinator, PlaybackTask
from services.recorded_call_builder import RecordedCallBuilderService


class ClientCallService:
    CAR_CALL_VOLUME_MULTIPLIER = 0.45

    def __init__(
        self,
        tk_root: tk.Tk,
        playback_coordinator: PlaybackCoordinator,
        call_builder: RecordedCallBuilderService,
        build_text_audio_file: Callable[[str], str],
        get_source_path: Callable[[], str],
        get_voice_message_path: Callable[[], str],
        get_device_name: Callable[[], str],
        get_voice_message_device_name: Callable[[], str],
        get_volume: Callable[[], float],
        get_voice_message_volume: Callable[[], float],
        get_speech_rate: Callable[[], float],
        is_number_trim_silence_enabled: Callable[[], bool],
        get_number_silence_threshold_db: Callable[[], int],
        get_number_trim_leading_padding_ms: Callable[[], int],
        get_number_trim_trailing_padding_ms: Callable[[], int],
        get_number_symbol_pause_ms: Callable[[], int],
        is_repeat_enabled: Callable[[], bool],
        get_repeat_interval_seconds: Callable[[], float],
        is_repeat_notification_enabled: Callable[[], bool],
        get_notification_volume: Callable[[], float],
        get_notification_sound_path: Callable[[], str],
        is_notification_enabled: Callable[[], bool],
        should_wait_for_priority: Callable[[], bool],
        on_state_change: Callable[[Optional[ClientCall], List[ClientCall], float], None],
        on_error: Callable[[str], None],
        on_log: Callable[[str], None],
        on_finished: Callable[[], None],
    ):
        self.root = tk_root
        self.playback_coordinator = playback_coordinator
        self.call_builder = call_builder
        self.build_text_audio_file = build_text_audio_file
        self.get_source_path = get_source_path
        self.get_voice_message_path = get_voice_message_path
        self.get_device_name = get_device_name
        self.get_voice_message_device_name = get_voice_message_device_name
        self.get_volume = get_volume
        self.get_voice_message_volume = get_voice_message_volume
        self.get_speech_rate = get_speech_rate
        self.is_number_trim_silence_enabled = is_number_trim_silence_enabled
        self.get_number_silence_threshold_db = get_number_silence_threshold_db
        self.get_number_trim_leading_padding_ms = get_number_trim_leading_padding_ms
        self.get_number_trim_trailing_padding_ms = get_number_trim_trailing_padding_ms
        self.get_number_symbol_pause_ms = get_number_symbol_pause_ms
        self.is_repeat_enabled = is_repeat_enabled
        self.get_repeat_interval_seconds = get_repeat_interval_seconds
        self.is_repeat_notification_enabled = is_repeat_notification_enabled
        self.get_notification_volume = get_notification_volume
        self.get_notification_sound_path = get_notification_sound_path
        self.is_notification_enabled = is_notification_enabled
        self.should_wait_for_priority = should_wait_for_priority
        self.on_state_change = on_state_change
        self.on_error = on_error
        self.on_log = on_log
        self.on_finished = on_finished

        self._queue: Deque[ClientCall] = deque()
        self._running = False
        self._last_signature: Optional[str] = None
        self._current_call: Optional[ClientCall] = None
        self._current_call_started_at: Optional[float] = None
        self._current_call_duration: float = 0.0
        self._last_error_message: Optional[str] = None
        self._source_initialized = False
        self._voice_message_initialized = False
        self._playback_requested = False
        self._last_voice_message_signature: Optional[str] = None
        self._call_build_generation = 0

    def start(self) -> None:
        self._running = True
        self._emit_state_change()
        self._poll_source_file()

    def stop(self) -> None:
        self._running = False
        self._call_build_generation += 1
        self._current_call = None
        self._current_call_started_at = None
        self._current_call_duration = 0.0
        self._playback_requested = False
        self._last_voice_message_signature = None
        self._voice_message_initialized = False
        self._emit_state_change()

    def enqueue_external_call(self, call: ClientCall) -> None:
        self._enqueue_calls([call])

    def resume_if_idle(self) -> None:
        self._play_next_if_idle()

    def stop_current_playback(self) -> None:
        self._call_build_generation += 1
        self._reset_current_call(remove_from_queue=True)
        self.root.after(0, self._play_next_if_idle)

    def remove_queued_call(self, call_id: str) -> None:
        if not call_id:
            return
        self._queue = deque(call for call in self._queue if call.call_id != call_id)
        self._emit_state_change()

    def _poll_source_file(self) -> None:
        if not self._running:
            return

        file_path = self.get_source_path().strip()
        if file_path and os.path.exists(file_path):
            try:
                raw_text = self._read_text(file_path)
                signature = hashlib.sha1(raw_text.encode("utf-8")).hexdigest()
                if signature != self._last_signature:
                    if not self._source_initialized:
                        self._last_signature = signature
                        self._source_initialized = True
                        self._clear_last_error()
                        self._schedule_source_poll()
                        return

                    self._last_signature = signature
                    calls = self._parse_calls(raw_text)
                    if calls:
                        self._enqueue_calls(calls)
                self._clear_last_error()
            except Exception as exc:
                self._report_poll_error("Ошибка чтения вызовов", exc)
        elif file_path:
            self._last_signature = None
            self._source_initialized = False
        else:
            self._source_initialized = False

        self._poll_voice_message_file()
        self._schedule_source_poll()

    def _poll_voice_message_file(self) -> None:
        file_path = self.get_voice_message_path().strip()
        if file_path and os.path.exists(file_path):
            try:
                signature = self._build_file_signature(file_path)
                if signature != self._last_voice_message_signature:
                    if not self._voice_message_initialized:
                        self._last_voice_message_signature = signature
                        self._voice_message_initialized = True
                        return

                    self._last_voice_message_signature = signature
                    self._enqueue_calls([self._build_voice_message_call(file_path)])
            except Exception as exc:
                self._report_poll_error("Ошибка чтения голосового сообщения", exc)
        elif file_path:
            self._last_voice_message_signature = None
            self._voice_message_initialized = False
        else:
            self._voice_message_initialized = False

    def _build_file_signature(self, file_path: str) -> str:
        stat_result = os.stat(file_path)
        return f"{stat_result.st_mtime_ns}:{stat_result.st_size}"

    def _format_queue_log_message(self, call: ClientCall) -> str:
        return f"Добавлено в очередь - {call.display_text}"

    def _read_text(self, file_path: str) -> str:
        encodings = ("utf-8-sig", "utf-8", "cp1251")
        last_error: Optional[Exception] = None
        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError as exc:
                last_error = exc

        if last_error:
            raise last_error

        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()

    def _parse_calls(self, raw_text: str) -> List[ClientCall]:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        if len(lines) == 1:
            message = lines[0]
            return [
                ClientCall(
                    start_choice="",
                    car_number="",
                    end_choice="",
                    display_message=message,
                    speech_text_override=message,
                    is_text_message=True,
                )
            ]

        calls: List[ClientCall] = []

        for index in range(0, len(lines), 3):
            chunk = lines[index:index + 3]
            if len(chunk) < 3:
                continue

            start_choice, car_number, end_choice = chunk

            calls.append(
                ClientCall(
                    start_choice=start_choice,
                    car_number=car_number,
                    end_choice=end_choice,
                    display_message=self.call_builder.build_display_text(
                        start_choice,
                        car_number,
                        end_choice,
                    ),
                )
            )

        return calls

    def _play_next_if_idle(self) -> None:
        if (
            self._playback_requested
            or self._current_call is not None
            or self.playback_coordinator.is_actively_playing
            or self.playback_coordinator.has_queued_tasks
            or self.should_wait_for_priority()
            or not self._queue
        ):
            return

        next_call = self._queue[0]
        self._current_call = next_call
        self._playback_requested = True
        self._emit_state_change()

        build_generation = self._call_build_generation
        threading.Thread(
            target=self._prepare_playback_worker,
            args=(next_call, build_generation),
            daemon=True,
        ).start()

    def _prepare_playback_worker(self, call: ClientCall, build_generation: int) -> None:
        try:
            temp_file, is_car_call = self._build_call_audio_file(call)
        except Exception as exc:
            error_message = str(exc)
            self._post_to_ui(lambda: self._handle_call_build_error(error_message, build_generation))
            return

        posted = self._post_to_ui(
            lambda: self._handle_call_audio_ready(call, temp_file, is_car_call, build_generation)
        )
        if not posted:
            self._cleanup_temp_file(temp_file)

    def _build_call_audio_file(self, call: ClientCall) -> tuple[str, bool]:
        if call.audio_file_path:
            return self._prepare_voice_message_file(call.audio_file_path), False

        if call.is_text_message:
            return self.build_text_audio_file(call.speech_text), False

        is_car_call = self.call_builder.should_repeat_car_call(call.car_number)
        repeat_car_call = self.is_repeat_enabled() and is_car_call
        base_file = self.call_builder.build_audio_file(
            call.start_choice,
            call.car_number,
            call.end_choice,
            playback_rate=self.get_speech_rate(),
            trim_silence_enabled=self.is_number_trim_silence_enabled(),
            silence_threshold_db=self.get_number_silence_threshold_db(),
            trim_leading_padding_ms=self.get_number_trim_leading_padding_ms(),
            trim_trailing_padding_ms=self.get_number_trim_trailing_padding_ms(),
            symbol_pause_ms=self.get_number_symbol_pause_ms(),
            repeat_count=1,
            pause_seconds=0.0,
        )
        if not repeat_car_call:
            return base_file, is_car_call

        repeated_file = self._build_repeated_car_call_file(base_file)
        self._cleanup_temp_file(base_file)
        return repeated_file, is_car_call

    def _handle_call_audio_ready(
        self,
        call: ClientCall,
        file_path: str,
        is_car_call: bool,
        build_generation: int,
    ) -> None:
        if (
            build_generation != self._call_build_generation
            or self._current_call is None
            or self._current_call.call_id != call.call_id
        ):
            self._cleanup_temp_file(file_path)
            return

        self._enqueue_playback_tasks(call, file_path, is_car_call)

    def _post_to_ui(self, callback: Callable[[], None]) -> bool:
        try:
            self.root.after(0, callback)
        except (RuntimeError, tk.TclError):
            return False
        return True

    def _handle_playback_started(self, duration: float) -> None:
        if self._current_call_started_at is not None:
            return

        self._current_call_duration = duration
        self._current_call_started_at = time.monotonic()
        self._schedule_progress_update()

    def _handle_playback_error(self, message: str) -> None:
        self.on_error(message)
        self._reset_current_call(remove_from_queue=True)
        self.root.after(0, self._play_next_if_idle)

    def _handle_playback_finished(self) -> None:
        self._reset_current_call(remove_from_queue=True)
        self.on_finished()
        self._play_next_if_idle()

    def _run_on_ui_thread(self, callback: Callable[[], None]) -> Callable[[], None]:
        return lambda: self.root.after(0, callback)

    def _build_started_callback(self, duration: float | None = None) -> Callable[[float], None]:
        return lambda actual_duration: self.root.after(
            0,
            lambda: self._handle_playback_started(duration if duration is not None else actual_duration),
        )

    def _build_error_callback(self) -> Callable[[str], None]:
        return lambda message: self.root.after(0, self._handle_playback_error, message)

    def _schedule_progress_update(self) -> None:
        if not self._running or self._current_call is None:
            return

        self._emit_state_change()
        if self._current_call is not None:
            self.root.after(100, self._schedule_progress_update)

    def _emit_state_change(self) -> None:
        self.on_state_change(self._current_call, list(self._queue), self._get_current_progress())

    def _get_current_progress(self) -> float:
        if self._current_call is None or self._current_call_started_at is None or self._current_call_duration <= 0:
            return 0.0

        elapsed = time.monotonic() - self._current_call_started_at
        return max(0.0, min(elapsed / self._current_call_duration, 1.0))

    def _reset_current_call(self, remove_from_queue: bool = False) -> None:
        if remove_from_queue and self._current_call is not None:
            self._remove_current_call_from_queue()
        self._current_call = None
        self._current_call_started_at = None
        self._current_call_duration = 0.0
        self._playback_requested = False
        self._emit_state_change()

    def _remove_current_call_from_queue(self) -> None:
        if self._current_call is None:
            return
        current_call_id = self._current_call.call_id
        if self._queue and self._queue[0].call_id == current_call_id:
            self._queue.popleft()
            return
        self._queue = deque(call for call in self._queue if call.call_id != current_call_id)

    def _resolve_call_volume(self, is_car_call: bool) -> float:
        base_volume = self.get_volume()
        if not is_car_call:
            return base_volume
        return max(0.0, min(base_volume * self.CAR_CALL_VOLUME_MULTIPLIER, 1.0))

    def _resolve_voice_message_volume(self) -> float:
        base_volume = self.get_volume()
        relative_volume = self.get_voice_message_volume()
        return max(0.0, min(base_volume * relative_volume, 1.0))

    def _prepare_voice_message_file(self, file_path: str) -> str:
        data, sample_rate = sf.read(file_path, dtype="float32", always_2d=True)
        cleaned = self._denoise_voice_message(data, sample_rate)
        temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(temp_fd)
        sf.write(temp_path, cleaned, sample_rate)
        return temp_path

    def _build_repeated_car_call_file(self, base_file_path: str) -> str:
        base_data, sample_rate = self._read_audio_file(base_file_path)
        segments = [base_data]

        repeat_interval = max(self.get_repeat_interval_seconds(), 0.0)
        interval_silence = self._build_silence(sample_rate, base_data.shape[1], repeat_interval)
        if interval_silence is not None:
            segments.append(interval_silence)

        if self.is_repeat_notification_enabled() and self.is_notification_enabled():
            notification_path = self.get_notification_sound_path().strip()
            if not notification_path or not os.path.exists(notification_path):
                self.on_error("Не найден файл звука уведомления")
            else:
                notification_data, notification_rate = self._read_audio_file(notification_path)
                notification_data = self._resample_audio(notification_data, notification_rate, sample_rate)
                notification_data = self._match_channel_count(notification_data, base_data.shape[1])
                notification_data = np.clip(
                    notification_data * float(self.get_notification_volume()),
                    -1.0,
                    1.0,
                ).astype("float32")
                segments.append(notification_data)

        segments.append(base_data)
        merged = np.concatenate(segments, axis=0)
        temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(temp_fd)
        sf.write(temp_path, merged, sample_rate)
        return temp_path

    def _read_audio_file(self, file_path: str) -> tuple[np.ndarray, int]:
        data, sample_rate = sf.read(file_path, dtype="float32", always_2d=True)
        if data.shape[1] > 2:
            data = data[:, :2]
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        return data.astype("float32"), sample_rate

    def _get_audio_duration(self, file_path: str) -> float:
        if not file_path or not os.path.exists(file_path):
            return 0.0

        try:
            return float(sf.info(file_path).duration)
        except (OSError, RuntimeError, TypeError, ValueError):
            return 0.0

    def _build_silence(self, sample_rate: int, channels: int, duration_seconds: float) -> np.ndarray | None:
        frame_count = int(round(sample_rate * max(duration_seconds, 0.0)))
        if frame_count <= 0:
            return None
        return np.zeros((frame_count, channels), dtype="float32")

    def _resample_audio(self, data: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
        if source_rate == target_rate or len(data) == 0:
            return data.astype("float32")

        source_positions = np.linspace(0.0, 1.0, num=len(data), endpoint=False, dtype=np.float64)
        target_length = max(1, int(round(len(data) * target_rate / source_rate)))
        target_positions = np.linspace(0.0, 1.0, num=target_length, endpoint=False, dtype=np.float64)
        channels = [
            np.interp(target_positions, source_positions, data[:, channel]).astype("float32")
            for channel in range(data.shape[1])
        ]
        return np.column_stack(channels).astype("float32")

    def _match_channel_count(self, data: np.ndarray, target_channels: int) -> np.ndarray:
        if data.shape[1] == target_channels:
            return data
        if data.shape[1] > target_channels:
            return data[:, :target_channels]
        if data.shape[1] == 1 and target_channels == 2:
            return np.repeat(data, 2, axis=1)
        return data

    def _denoise_voice_message(self, data: np.ndarray, sample_rate: int) -> np.ndarray:
        if data.size == 0:
            return data

        working = data.astype("float32", copy=True)
        if working.shape[1] > 2:
            working = working[:, :2]

        # Remove DC offset so constant bias does not inflate the noise floor.
        working -= np.mean(working, axis=0, keepdims=True)

        amplitude = np.max(np.abs(working), axis=1)
        if amplitude.size == 0:
            return working

        sample_window = min(len(amplitude), max(int(sample_rate * 0.3), 1))
        noise_floor = float(np.percentile(amplitude[:sample_window], 35))
        noise_floor = max(noise_floor, 0.0015)
        hard_gate = noise_floor * 0.95
        soft_gate = noise_floor * 2.1

        gains = np.ones_like(amplitude, dtype="float32")
        quiet_mask = amplitude < hard_gate
        soft_mask = (amplitude >= hard_gate) & (amplitude < soft_gate)
        gains[quiet_mask] = 0.55
        if np.any(soft_mask):
            gains[soft_mask] = np.interp(
                amplitude[soft_mask],
                [hard_gate, soft_gate],
                [0.7, 1.0],
            ).astype("float32")

        smoothed_gains = self._smooth_envelope(gains, attack=512, release=8192)
        cleaned = working * smoothed_gains[:, None]
        return np.clip(cleaned, -1.0, 1.0).astype("float32")

    def _smooth_envelope(self, gains: np.ndarray, attack: int, release: int) -> np.ndarray:
        if gains.size == 0:
            return gains

        smoothed = np.empty_like(gains, dtype="float32")
        current = float(gains[0])
        attack_alpha = 1.0 / max(attack, 1)
        release_alpha = 1.0 / max(release, 1)

        for index, target in enumerate(gains):
            alpha = attack_alpha if target > current else release_alpha
            current += (float(target) - current) * alpha
            smoothed[index] = current

        return smoothed

    def _enqueue_calls(self, calls: List[ClientCall]) -> None:
        if not calls:
            return
        self._queue.extend(calls)
        for call in calls:
            self.on_log(self._format_queue_log_message(call))
        self._emit_state_change()
        self._play_next_if_idle()

    def _build_voice_message_call(self, file_path: str) -> ClientCall:
        return ClientCall(
            start_choice="",
            car_number="",
            end_choice="",
            display_message=os.path.basename(file_path),
            audio_file_path=file_path,
        )

    def _clear_last_error(self) -> None:
        self._last_error_message = None

    def _report_poll_error(self, prefix: str, error: Exception) -> None:
        message = f"{prefix}: {error}"
        if message != self._last_error_message:
            self._last_error_message = message
            self.on_error(message)

    def _schedule_source_poll(self) -> None:
        self.root.after(300, self._poll_source_file)

    def _handle_call_build_error(self, error_message: str, build_generation: int | None = None) -> None:
        if build_generation is not None and build_generation != self._call_build_generation:
            return

        self._reset_current_call(remove_from_queue=True)
        self.on_error(f"Не удалось собрать вызов: {error_message}")
        self.root.after(0, self._play_next_if_idle)

    def _cleanup_temp_file(self, file_path: str) -> None:
        if not file_path or not os.path.exists(file_path):
            return

        try:
            os.remove(file_path)
        except OSError:
            pass

    def _enqueue_playback_tasks(self, call: ClientCall, file_path: str, is_car_call: bool) -> None:
        total_duration = self._get_audio_duration(file_path)
        notification_task = self._build_notification_task(call, total_duration)
        if notification_task is not None:
            total_duration += self._get_audio_duration(notification_task.file_path)
            notification_task.on_started = self._build_started_callback(total_duration)
            self.playback_coordinator.enqueue(notification_task)

        self.playback_coordinator.enqueue(self._build_voice_task(call, file_path, is_car_call))

    def _build_voice_task(self, call: ClientCall, file_path: str, is_car_call: bool) -> PlaybackTask:
        return PlaybackTask(
            file_path=file_path,
            volume=(
                self._resolve_voice_message_volume()
                if call.audio_file_path
                else self._resolve_call_volume(is_car_call=is_car_call)
            ),
            device_name=self.get_voice_message_device_name() if call.audio_file_path else self.get_device_name(),
            group_id=call.call_id or "",
            cleanup_file=True,
            use_cooldown=True,
            on_started=self._build_started_callback(),
            on_finished=self._run_on_ui_thread(self._handle_playback_finished),
            on_error=self._build_error_callback(),
        )

    def _build_notification_task(self, call: ClientCall, total_duration: float) -> Optional[PlaybackTask]:
        if not self.is_notification_enabled():
            return None

        notification_sound_path = self.get_notification_sound_path().strip()
        if not notification_sound_path or not os.path.exists(notification_sound_path):
            self.on_error("Не найден файл звука уведомления")
            return None

        return PlaybackTask(
            file_path=notification_sound_path,
            volume=self.get_notification_volume(),
            device_name=self.get_device_name(),
            group_id=call.call_id or "",
            on_started=self._build_started_callback(total_duration),
            on_error=self._build_error_callback(),
        )
