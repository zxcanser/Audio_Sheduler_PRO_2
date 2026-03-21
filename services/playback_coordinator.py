from collections import deque
from dataclasses import dataclass
import os
from typing import Callable, Deque, Optional

import tkinter as tk
import soundfile as sf

from services.audio_player import AudioPlayer


@dataclass
class PlaybackTask:
    file_path: str
    volume: float
    device_name: str
    cleanup_file: bool = False
    use_cooldown: bool = False
    on_started: Optional[Callable[[float], None]] = None
    on_finished: Optional[Callable[[], None]] = None
    on_error: Optional[Callable[[str], None]] = None


class PlaybackCoordinator:
    def __init__(
        self,
        tk_root: tk.Tk,
        player: AudioPlayer,
        get_interval_seconds: Callable[[], float],
    ):
        self.root = tk_root
        self.player = player
        self.get_interval_seconds = get_interval_seconds
        self._queue: Deque[PlaybackTask] = deque()
        self._current_task: Optional[PlaybackTask] = None
        self._cooldown_active = False

    @property
    def is_busy(self) -> bool:
        return self._current_task is not None or self._cooldown_active or self.player.is_playing

    @property
    def is_actively_playing(self) -> bool:
        return self._current_task is not None or self.player.is_playing

    def enqueue(self, task: PlaybackTask) -> None:
        self._queue.append(task)
        self._play_next_if_possible()

    def stop(self) -> None:
        self.player.stop()

    def reset(self) -> None:
        self.player.stop()
        self._queue.clear()
        self._current_task = None
        self._cooldown_active = False

    def _play_next_if_possible(self) -> None:
        if self._current_task is not None or self._cooldown_active or self.player.is_playing or not self._queue:
            return

        task = self._queue.popleft()
        self._current_task = task

        try:
            duration = float(sf.info(task.file_path).duration)
        except Exception:
            duration = 0.0

        if task.on_started:
            task.on_started(duration)

        self.player.play_async(
            file_path=task.file_path,
            volume=task.volume,
            device_name=task.device_name,
            on_error=lambda message: self.root.after(0, lambda: self._handle_error(message)),
            on_finished=lambda: self.root.after(0, self._handle_finished),
        )

    def _handle_finished(self) -> None:
        task = self._current_task
        self._cleanup_current_task_file()
        self._current_task = None

        if task and task.on_finished:
            task.on_finished()

        self._schedule_cooldown(task)

    def _handle_error(self, message: str) -> None:
        task = self._current_task
        self._cleanup_current_task_file()
        self._current_task = None

        if task and task.on_error:
            task.on_error(message)

        self._schedule_cooldown(task)

    def _schedule_cooldown(self, task: Optional[PlaybackTask]) -> None:
        if task is None or not task.use_cooldown:
            self._play_next_if_possible()
            return

        interval_ms = int(max(self.get_interval_seconds(), 0.0) * 1000)
        if interval_ms <= 0:
            self._play_next_if_possible()
            return

        self._cooldown_active = True
        self.root.after(interval_ms, self._finish_cooldown)

    def _finish_cooldown(self) -> None:
        self._cooldown_active = False
        self._play_next_if_possible()

    def _cleanup_current_task_file(self) -> None:
        task = self._current_task
        if not task or not task.cleanup_file:
            return

        if os.path.exists(task.file_path):
            try:
                os.remove(task.file_path)
            except OSError:
                pass
