from datetime import datetime, date, time, timedelta
from typing import Callable, List, Optional

from models import ScheduleEntry


class SchedulerService:
    def __init__(
        self,
        tk_root,
        get_entries: Callable[[], List[ScheduleEntry]],
        is_workday: Callable[[], bool],
        on_trigger: Callable[[ScheduleEntry], None],
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self.root = tk_root
        self.get_entries = get_entries
        self.is_workday = is_workday
        self.on_trigger = on_trigger
        self.on_error = on_error
        self._last_run: dict[str, tuple[date, str]] = {}
        self._last_tick_at: datetime | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._last_tick_at = None
        self._tick()

    def stop(self) -> None:
        self._running = False
        self._last_tick_at = None

    def _tick(self) -> None:
        if not self._running:
            return

        try:
            self._run_due_entries()
        except Exception as error:
            self._report_error(f"Ошибка планировщика: {error}")
        finally:
            if self._running:
                self.root.after(1000, self._tick)

    def _run_due_entries(self) -> None:
        now = datetime.now()
        today = now.date()
        first_tick = self._last_tick_at is None
        window_start = self._get_trigger_window_start(now)
        self._last_tick_at = now

        if not self.is_workday():
            return

        for entry in self.get_entries():
            if not entry.enabled:
                continue

            scheduled_at = self._scheduled_datetime(today, entry.time_str)
            if scheduled_at is None:
                continue

            is_due = window_start <= scheduled_at <= now
            if first_tick:
                is_due = scheduled_at.strftime("%H:%M") == now.strftime("%H:%M")

            run_signature = (today, entry.time_str)
            if is_due and self._last_run.get(entry.entry_id) != run_signature:
                self._trigger_entry(entry, today)

    def _trigger_entry(self, entry: ScheduleEntry, today: date) -> None:
        try:
            self.on_trigger(entry)
        except Exception as error:
            self._report_error(f"Ошибка запуска расписания {entry.time_str} | {entry.file_name}: {error}")
            return
        self._last_run[entry.entry_id] = (today, entry.time_str)

    def _get_trigger_window_start(self, now: datetime) -> datetime:
        if self._last_tick_at is None:
            return now.replace(second=0, microsecond=0)
        return max(self._last_tick_at, now - timedelta(minutes=2))

    def _scheduled_datetime(self, target_date: date, time_str: str) -> datetime | None:
        try:
            hour_text, minute_text = time_str.split(":", 1)
            scheduled_time = time(int(hour_text), int(minute_text))
        except (TypeError, ValueError):
            return None
        return datetime.combine(target_date, scheduled_time)

    def _report_error(self, message: str) -> None:
        if self.on_error:
            self.on_error(message)
