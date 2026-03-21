from datetime import datetime, date
from typing import Callable, List

from models import ScheduleEntry


class SchedulerService:
    def __init__(
        self,
        tk_root,
        get_entries: Callable[[], List[ScheduleEntry]],
        on_trigger: Callable[[ScheduleEntry], None],
    ):
        self.root = tk_root
        self.get_entries = get_entries
        self.on_trigger = on_trigger
        self._last_run: dict[str, date] = {}
        self._running = False

    def start(self) -> None:
        self._running = True
        self._tick()

    def stop(self) -> None:
        self._running = False

    def _tick(self) -> None:
        if not self._running:
            return

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        today = now.date()

        for entry in self.get_entries():
            if not entry.enabled:
                continue

            if entry.time_str == current_time and self._last_run.get(entry.entry_id) != today:
                self._last_run[entry.entry_id] = today
                self.on_trigger(entry)

        self.root.after(1000, self._tick)