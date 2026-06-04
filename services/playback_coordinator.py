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
    group_id: str = ""
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
        self._playback_generation = 0

    @property
    def is_actively_playing(self) -> bool:
        return self._current_task is not None or self.player.is_playing

    @property
    def has_queued_tasks(self) -> bool:
        return bool(self._queue)

    def enqueue(self, task: PlaybackTask) -> None:
        self._queue.append(task)
        self._play_next_if_possible()

    def enqueue_batch(self, tasks: list[PlaybackTask], front: bool = False) -> None:
        if front:
            for task in reversed(tasks):
                self._queue.appendleft(task)
        else:
            self._queue.extend(tasks)
        self._play_next_if_possible()

    def remove_group(self, group_id: str) -> None:
        if not group_id:
            return
        self._queue = deque(task for task in self._queue if task.group_id != group_id)

    def stop(self) -> None:
        self._playback_generation += 1
        self._clear_playback_state(clear_queue=True)
        self.player.stop()

    def stop_current_group(self) -> None:
        current_task = self._current_task
        current_group_id = current_task.group_id if current_task is not None else ""

        self._playback_generation += 1
        self._clear_playback_state(clear_queue=False)
        self.player.stop()

        if current_group_id:
            self.remove_group(current_group_id)

        self.root.after(0, self._play_next_if_possible)

    def reset(self) -> None:
        self._playback_generation += 1
        self.player.stop()
        self._clear_playback_state(clear_queue=True)

    def _play_next_if_possible(self) -> None:
        if self._current_task is not None or self._cooldown_active or self.player.is_playing or not self._queue:
            return

        task = self._queue.popleft()
        self._current_task = task
        generation = self._playback_generation

        duration = self._get_task_duration(task)

        if task.on_started:
            task.on_started(duration)

        self.player.play_async(
            file_path=task.file_path,
            volume=task.volume,
            device_name=task.device_name,
            on_error=lambda message, playback_generation=generation: self.root.after(
                0,
                lambda: self._handle_error(message, playback_generation),
            ),
            on_finished=lambda playback_generation=generation: self.root.after(
                0,
                lambda: self._handle_finished(playback_generation),
            ),
        )

    def _handle_finished(self, playback_generation: int) -> None:
        if playback_generation != self._playback_generation:
            return

        task = self._current_task
        self._cleanup_current_task_file()
        self._current_task = None

        if task and task.on_finished:
            task.on_finished()

        self._schedule_cooldown(task)

    def _handle_error(self, message: str, playback_generation: int) -> None:
        if playback_generation != self._playback_generation:
            return

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

    def _clear_playback_state(self, clear_queue: bool) -> None:
        self._cleanup_current_task_file()
        if clear_queue:
            self._queue.clear()
        self._current_task = None
        self._cooldown_active = False

    def _get_task_duration(self, task: PlaybackTask) -> float:
        try:
            return float(sf.info(task.file_path).duration)
        except (OSError, RuntimeError, TypeError, ValueError):
            return 0.0
