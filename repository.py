import json
import os
import shutil
from dataclasses import asdict
from typing import Any, List

from config import LEGACY_CONFIG_FILES, LEGACY_SCHEDULE_FILES
from models import AppSettings, ScheduleEntry


class JsonRepository:
    def __init__(self, config_path: str, schedule_path: str):
        self.config_path = config_path
        self.schedule_path = schedule_path

    def load_settings(self) -> AppSettings:
        self._migrate_legacy_file_if_needed(self.config_path, LEGACY_CONFIG_FILES)
        data = self._load_json_object(self.config_path)
        if data is None:
            return AppSettings()

        try:
            return AppSettings(
                selected_device=data.get("selected_device", ""),
                volume=data.get("volume", 0.8),
                notification_volume=data.get("notification_volume", data.get("volume", 0.8)),
                notification_sound_file_path=data.get("notification_sound_file_path", ""),
                autostart_enabled=data.get("autostart_enabled", False),
                scheduler_notification_enabled=data.get("scheduler_notification_enabled", False),
                client_calls_notification_enabled=data.get("client_calls_notification_enabled", False),
                client_calls_file_path=data.get("client_calls_file_path", ""),
                client_calls_api_enabled=data.get("client_calls_api_enabled", False),
                client_calls_api_host=data.get("client_calls_api_host", "127.0.0.1"),
                client_calls_api_port=int(data.get("client_calls_api_port", 8765)),
                client_calls_api_token=data.get("client_calls_api_token", ""),
                client_calls_voice_message_file_path=data.get("client_calls_voice_message_file_path", ""),
                client_calls_selected_device=data.get("client_calls_selected_device", ""),
                client_calls_voice_message_selected_device=data.get(
                    "client_calls_voice_message_selected_device",
                    data.get("client_calls_selected_device", ""),
                ),
                client_calls_volume=data.get("client_calls_volume", 0.8),
                client_calls_voice_message_volume=data.get("client_calls_voice_message_volume", 1.0),
                client_calls_speech_rate=data.get("client_calls_speech_rate", 1.0),
                number_trim_silence_enabled=data.get("number_trim_silence_enabled", True),
                number_silence_threshold_db=self._normalize_int(
                    data.get("number_silence_threshold_db"),
                    default=-42,
                    minimum=-70,
                    maximum=-20,
                ),
                number_trim_leading_padding_ms=self._normalize_int(
                    data.get("number_trim_leading_padding_ms"),
                    default=20,
                    minimum=0,
                    maximum=300,
                ),
                number_trim_trailing_padding_ms=self._normalize_int(
                    data.get("number_trim_trailing_padding_ms"),
                    default=55,
                    minimum=0,
                    maximum=500,
                ),
                number_symbol_pause_ms=self._normalize_int(
                    data.get("number_symbol_pause_ms"),
                    default=120,
                    minimum=0,
                    maximum=500,
                ),
                client_calls_interval_seconds=data.get("client_calls_interval_seconds", 5.0),
                client_calls_repeat_enabled=data.get("client_calls_repeat_enabled", False),
                client_calls_repeat_interval_seconds=data.get("client_calls_repeat_interval_seconds", 3.0),
                client_calls_repeat_notification_enabled=data.get("client_calls_repeat_notification_enabled", False),
                client_calls_text_voice=data.get("client_calls_text_voice", ""),
                client_calls_text_voice_id=data.get("client_calls_text_voice_id", ""),
                client_calls_text_language_code=data.get("client_calls_text_language_code", ""),
                employees_file_path=data.get("employees_file_path", ""),
                generator_api_key=self._load_generator_api_key(data),
                generator_selected_device=data.get("generator_selected_device", ""),
                generator_volume=data.get("generator_volume", 0.8),
                generator_master_volume=self._normalize_generator_master_volume(data.get("generator_master_volume")),
                generator_language_code=data.get("generator_language_code", "ru-RU"),
                generator_accent_code=data.get("generator_accent_code", ""),
                generator_speed=int(data.get("generator_speed", 0)),
                generator_voice=data.get("generator_voice", ""),
                generator_voice_id=data.get("generator_voice_id", ""),
                main_window_geometry=data.get("main_window_geometry", ""),
            )
        except (TypeError, ValueError):
            return AppSettings()

    def _load_generator_api_key(self, data: dict) -> str:
        direct_key = str(data.get("generator_api_key", "") or "").strip()
        if direct_key:
            return direct_key

        legacy_path = str(data.get("generator_api_file_path", "") or "").strip()
        if not legacy_path or not os.path.exists(legacy_path):
            return ""

        try:
            with open(legacy_path, "r", encoding="utf-8") as file:
                for line in file:
                    key = line.strip()
                    if key:
                        if key.lower().startswith("bearer "):
                            return key[7:].strip()
                        return key
        except OSError:
            return ""
        return ""

    def save_settings(self, settings: AppSettings) -> None:
        self._ensure_parent_dir(self.config_path)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(settings), f, ensure_ascii=False, indent=2)

    def load_schedule(self) -> List[ScheduleEntry]:
        self._migrate_legacy_file_if_needed(self.schedule_path, LEGACY_SCHEDULE_FILES)
        raw_data = self._load_json_object(self.schedule_path)
        if not isinstance(raw_data, list):
            return []

        try:
            return [
                ScheduleEntry(
                    time_str=item["time_str"],
                    file_path=item["file_path"],
                    enabled=item.get("enabled", True),
                    entry_id=item.get("entry_id") or item.get("id"),
                )
                for item in raw_data
            ]
        except (TypeError, KeyError):
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

    def _normalize_generator_master_volume(self, value) -> int:
        try:
            numeric_value = int(value)
        except (TypeError, ValueError):
            return 100

        if -20 <= numeric_value <= 20:
            converted = 100 + numeric_value * 2
            return max(50, min(150, converted))

        return max(50, min(150, numeric_value))

    def _normalize_int(self, value, default: int, minimum: int, maximum: int) -> int:
        try:
            numeric_value = int(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, numeric_value))

    def _load_json_object(self, file_path: str) -> Any | None:
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

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
