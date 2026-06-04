import os
import threading
from typing import Callable, Optional

import sounddevice as sd
import soundfile as sf

from services.audio_device_service import AudioDeviceService


class AudioPlayer:
    def __init__(self, device_service: AudioDeviceService):
        self.device_service = device_service
        self._thread: Optional[threading.Thread] = None
        self._is_playing = False
        self._lock = threading.Lock()

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def play_async(
        self,
        file_path: str,
        volume: float,
        device_name: str,
        on_error: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[], None]] = None,
    ) -> None:
        if self._is_playing:
            self.stop()

        self._thread = threading.Thread(
            target=self._play_worker,
            args=(file_path, volume, device_name, on_error, on_finished),
            daemon=True,
        )
        self._thread.start()

    def _play_worker(
        self,
        file_path: str,
        volume: float,
        device_name: str,
        on_error: Optional[Callable[[str], None]],
        on_finished: Optional[Callable[[], None]],
    ) -> None:
        with self._lock:
            self._is_playing = True

        playback_failed = False

        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Файл не найден: {file_path}")

            data, samplerate = sf.read(file_path, dtype="float32")
            data = self._normalize_audio_data(data) * volume
            self._play_on_output_device(data, samplerate, device_name)

            sd.wait()

        except Exception as e:
            playback_failed = True
            if on_error:
                on_error(str(e))
        finally:
            with self._lock:
                self._is_playing = False
            if not playback_failed and on_finished:
                on_finished()

    def stop(self) -> None:
        sd.stop()
        with self._lock:
            self._is_playing = False

    def _normalize_audio_data(self, data):
        if data.ndim == 2 and data.shape[1] > 2:
            return data[:, :2]
        return data

    def _play_on_output_device(self, data, samplerate: int, device_name: str) -> None:
        device_id = self.device_service.get_device_id_by_name(device_name) if device_name else None

        # На macOS иногда выбранное устройство возвращает ошибку AUHAL -50.
        # Поэтому если устройство не найдено или сломалось — пробуем системное по умолчанию.
        if device_id is None:
            sd.play(data, samplerate)
            return

        try:
            sd.play(data, samplerate, device=device_id)
        except Exception:
            sd.play(data, samplerate)
