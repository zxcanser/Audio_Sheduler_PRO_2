import json
import os
import shutil
from dataclasses import asdict
from typing import List

from config import LEGACY_CONFIG_FILES, LEGACY_SCHEDULE_FILES
from models import AppSettings, ScheduleEntry


class JsonRepository:
    def __init__(self, config_path: str, schedule_path: str):
        self.config_path = config_path
        self.schedule_path = schedule_path

    def load_settings(self) -> AppSettings:
        self._migrate_legacy_file_if_needed(self.config_path, LEGACY_CONFIG_FILES)
        if not os.path.exists(self.config_path):
            return AppSettings()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            return AppSettings(
                selected_device=data.get("selected_device", ""),
                volume=data.get("volume", 0.8),
                notification_volume=data.get("notification_volume", data.get("volume", 0.8)),
                notification_sound_file_path=data.get("notification_sound_file_path", ""),
                autostart_enabled=data.get("autostart_enabled", False),
                scheduler_notification_enabled=data.get("scheduler_notification_enabled", False),
                client_calls_notification_enabled=data.get("client_calls_notification_enabled", False),
                client_calls_file_path=data.get("client_calls_file_path", ""),
                client_calls_voice_message_file_path=data.get("client_calls_voice_message_file_path", ""),
                client_calls_selected_device=data.get("client_calls_selected_device", ""),
                client_calls_voice_message_selected_device=data.get(
                    "client_calls_voice_message_selected_device",
                    data.get("client_calls_selected_device", ""),
                ),
                client_calls_volume=data.get("client_calls_volume", 0.8),
                client_calls_voice_message_volume=data.get("client_calls_voice_message_volume", 1.0),
                client_calls_speech_rate=data.get("client_calls_speech_rate", 1.0),
                client_calls_interval_seconds=data.get("client_calls_interval_seconds", 5.0),
                client_calls_repeat_enabled=data.get("client_calls_repeat_enabled", False),
                client_calls_repeat_interval_seconds=data.get("client_calls_repeat_interval_seconds", 3.0),
                client_calls_repeat_notification_enabled=data.get("client_calls_repeat_notification_enabled", False),
                client_calls_text_voice=data.get("client_calls_text_voice", ""),
                client_calls_text_voice_id=data.get("client_calls_text_voice_id", ""),
                client_calls_text_language_code=data.get("client_calls_text_language_code", ""),
                employees_file_path=data.get("employees_file_path", ""),
                generator_api_file_path=data.get("generator_api_file_path", ""),
                generator_selected_device=data.get("generator_selected_device", ""),
                generator_volume=data.get("generator_volume", 0.8),
                generator_language_code=data.get("generator_language_code", "ru-RU"),
                generator_voice=data.get("generator_voice", ""),
                generator_voice_id=data.get("generator_voice_id", ""),
                main_window_geometry=data.get("main_window_geometry", ""),
                scheduler_weekdays=self._normalize_weekdays(data.get("scheduler_weekdays")),
            )
        except Exception:
            return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        self._ensure_parent_dir(self.config_path)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(settings), f, ensure_ascii=False, indent=2)

    def load_schedule(self) -> List[ScheduleEntry]:
        self._migrate_legacy_file_if_needed(self.schedule_path, LEGACY_SCHEDULE_FILES)
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
        self._ensure_parent_dir(self.schedule_path)
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

    def _migrate_legacy_file_if_needed(self, current_path: str, legacy_paths: list[str]) -> None:
        if os.path.exists(current_path):
            return

        self._ensure_parent_dir(current_path)
        current_realpath = os.path.realpath(current_path)
        for legacy_path in legacy_paths:
            if not legacy_path or not os.path.exists(legacy_path):
                continue
            if os.path.realpath(legacy_path) == current_realpath:
                continue

            shutil.copy2(legacy_path, current_path)
            return

    def _ensure_parent_dir(self, file_path: str) -> None:
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
