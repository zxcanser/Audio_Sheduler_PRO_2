import json
import os
from dataclasses import asdict
from typing import List

from models import AppSettings, ScheduleEntry


class JsonRepository:
    def __init__(self, config_path: str, schedule_path: str):
        self.config_path = config_path
        self.schedule_path = schedule_path

    def load_settings(self) -> AppSettings:
        if not os.path.exists(self.config_path):
            return AppSettings()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return AppSettings(
                selected_device=data.get("selected_device", ""),
                volume=data.get("volume", 0.8),
                notification_sound_file_path=data.get("notification_sound_file_path", ""),
                scheduler_notification_enabled=data.get("scheduler_notification_enabled", False),
                client_calls_notification_enabled=data.get("client_calls_notification_enabled", False),
                client_calls_file_path=data.get("client_calls_file_path", ""),
                client_calls_selected_device=data.get("client_calls_selected_device", ""),
                client_calls_volume=data.get("client_calls_volume", 0.8),
                client_calls_interval_seconds=data.get("client_calls_interval_seconds", 5.0),
                scheduler_weekdays=self._normalize_weekdays(data.get("scheduler_weekdays")),
            )
        except Exception:
            return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(settings), f, ensure_ascii=False, indent=2)

    def load_schedule(self) -> List[ScheduleEntry]:
        if not os.path.exists(self.schedule_path):
            return []

        try:
            with open(self.schedule_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            entries: List[ScheduleEntry] = []
            for item in raw_data:
                entry = ScheduleEntry(
                    time_str=item["time_str"],
                    file_path=item["file_path"],
                    enabled=item.get("enabled", True),
                    entry_id=item.get("entry_id") or item.get("id"),
                )
                entries.append(entry)

            return entries

        except Exception:
            return []

    def save_schedule(self, entries: List[ScheduleEntry]) -> None:
        with open(self.schedule_path, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(entry) for entry in entries],
                f,
                ensure_ascii=False,
                indent=2,
            )

    def _normalize_weekdays(self, value) -> list[int]:
        if not isinstance(value, list):
            return [0, 1, 2, 3, 4, 5, 6]

        weekdays = sorted({day for day in value if isinstance(day, int) and 0 <= day <= 6})
        return weekdays if weekdays else [0, 1, 2, 3, 4, 5, 6]
