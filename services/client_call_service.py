import hashlib
import os
import time
from collections import deque
from datetime import datetime
from typing import Callable, Deque, List, Optional

import tkinter as tk

from config import CLIENT_CALLS_LOG_FILE
from models import ClientCall
from services.playback_coordinator import PlaybackCoordinator, PlaybackTask
from services.speech_synthesizer import SpeechSynthesizerService


class ClientCallService:
    def __init__(
        self,
        tk_root: tk.Tk,
        playback_coordinator: PlaybackCoordinator,
        synthesizer: SpeechSynthesizerService,
        get_source_path: Callable[[], str],
        get_device_name: Callable[[], str],
        get_volume: Callable[[], float],
        get_speech_rate: Callable[[], float],
        get_notification_volume: Callable[[], float],
        get_notification_sound_path: Callable[[], str],
        is_notification_enabled: Callable[[], bool],
        on_state_change: Callable[[Optional[ClientCall], List[ClientCall], float], None],
        on_error: Callable[[str], None],
    ):
        self.root = tk_root
        self.playback_coordinator = playback_coordinator
        self.synthesizer = synthesizer
        self.get_source_path = get_source_path
        self.get_device_name = get_device_name
        self.get_volume = get_volume
        self.get_speech_rate = get_speech_rate
        self.get_notification_volume = get_notification_volume
        self.get_notification_sound_path = get_notification_sound_path
        self.is_notification_enabled = is_notification_enabled
        self.on_state_change = on_state_change
        self.on_error = on_error

        self._queue: Deque[ClientCall] = deque()
        self._running = False
        self._last_signature: Optional[str] = None
        self._current_call: Optional[ClientCall] = None
        self._current_call_started_at: Optional[float] = None
        self._current_call_duration: float = 0.0
        self._last_error_message: Optional[str] = None
        self._source_initialized = False
        self._playback_requested = False

    def start(self) -> None:
        self._running = True
        self._emit_state_change()
        self._poll_source_file()

    def stop(self) -> None:
        self._running = False
        self._current_call = None
        self._current_call_started_at = None
        self._current_call_duration = 0.0
        self._playback_requested = False
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
                        self._last_error_message = None
                        self.root.after(300, self._poll_source_file)
                        return

                    self._last_signature = signature
                    calls = self._parse_calls(raw_text)
                    if calls:
                        self._append_calls_to_log(calls)
                        self._queue.extend(calls)
                        self._emit_state_change()
                        self._play_next_if_idle()
                self._last_error_message = None
            except Exception as exc:
                message = f"Ошибка чтения вызовов: {exc}"
                if message != self._last_error_message:
                    self._last_error_message = message
                    self.on_error(message)
        elif file_path:
            self._last_signature = None
            self._source_initialized = False
        else:
            self._source_initialized = False

        self.root.after(300, self._poll_source_file)

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
        calls: List[ClientCall] = []

        for index in range(0, len(lines), 3):
            chunk = lines[index:index + 3]
            if not chunk:
                continue

            counter = chunk[0]
            ticket = chunk[1] if len(chunk) > 1 else ""
            speech_message = " ".join(chunk)

            calls.append(
                ClientCall(
                    counter=counter,
                    ticket=ticket,
                    speech_message=speech_message,
                )
            )

        return calls

    def _append_calls_to_log(self, calls: List[ClientCall]) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            log_dir = os.path.dirname(CLIENT_CALLS_LOG_FILE)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            with open(CLIENT_CALLS_LOG_FILE, "a", encoding="utf-8") as log_file:
                for call in calls:
                    log_file.write(f"[{timestamp}] {call.display_text}\n")
        except OSError as exc:
            self.on_error(f"Не удалось записать лог вызовов: {exc}")

    def _play_next_if_idle(self) -> None:
        if self._playback_requested or self._current_call is not None or not self._queue:
            return

        next_call = self._queue.popleft()
        self._current_call = next_call
        self._playback_requested = True
        self._emit_state_change()

        try:
            temp_file = self.synthesizer.synthesize_to_file(
                next_call.speech_text,
                speech_rate=self.get_speech_rate(),
            )
        except Exception as exc:
            self._current_call = None
            self._playback_requested = False
            self.on_error(f"Не удалось озвучить вызов: {exc}")
            self._emit_state_change()
            self.root.after(0, self._play_next_if_idle)
            return

        voice_task = PlaybackTask(
            file_path=temp_file,
            volume=self.get_volume(),
            device_name=self.get_device_name(),
            cleanup_file=True,
            use_cooldown=True,
            on_started=lambda duration: self.root.after(0, lambda: self._handle_playback_started(duration)),
            on_finished=lambda: self.root.after(0, self._handle_playback_finished),
            on_error=lambda msg: self.root.after(0, lambda: self._handle_playback_error(msg)),
        )

        if self.is_notification_enabled():
            notification_sound_path = self.get_notification_sound_path().strip()
            if not notification_sound_path or not os.path.exists(notification_sound_path):
                self._current_call = None
                self._playback_requested = False
                self.on_error("Сначала выберите файл звука уведомления")
                self._emit_state_change()
                self.root.after(0, self._play_next_if_idle)
                return

            self.playback_coordinator.enqueue(
                PlaybackTask(
                    file_path=notification_sound_path,
                    volume=self.get_notification_volume(),
                    device_name=self.get_device_name(),
                    on_error=lambda msg: self.root.after(0, lambda: self._handle_playback_error(msg)),
                )
            )

        self.playback_coordinator.enqueue(voice_task)

    def _handle_playback_started(self, duration: float) -> None:
        self._current_call_duration = duration
        self._current_call_started_at = time.monotonic()
        self._schedule_progress_update()

    def _handle_playback_error(self, message: str) -> None:
        self.on_error(message)
        self._reset_current_call()

    def _handle_playback_finished(self) -> None:
        self._reset_current_call()
        self._play_next_if_idle()

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

    def _reset_current_call(self) -> None:
        self._current_call = None
        self._current_call_started_at = None
        self._current_call_duration = 0.0
        self._playback_requested = False
        self._emit_state_change()
