import os
import uuid
from dataclasses import dataclass
from typing import ClassVar, Optional


@dataclass
class ScheduleEntry:
    time_str: str
    file_path: str
    enabled: bool = True
    entry_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.entry_id:
            self.entry_id = str(uuid.uuid4())

    @property
    def file_name(self) -> str:
        return os.path.basename(self.file_path)


@dataclass
class AppSettings:
    selected_device: str = ""
    volume: float = 0.8
    notification_volume: float = 0.8
    notification_sound_file_path: str = ""
    autostart_enabled: bool = False
    scheduler_notification_enabled: bool = False
    client_calls_notification_enabled: bool = False
    client_calls_file_path: str = ""
    client_calls_api_enabled: bool = False
    client_calls_api_host: str = "127.0.0.1"
    client_calls_api_port: int = 8765
    client_calls_api_token: str = ""
    client_calls_voice_message_file_path: str = ""
    client_calls_selected_device: str = ""
    client_calls_voice_message_selected_device: str = ""
    client_calls_volume: float = 0.8
    client_calls_voice_message_volume: float = 1.0
    client_calls_speech_rate: float = 1.0
    number_trim_silence_enabled: bool = True
    number_silence_threshold_db: int = -42
    number_trim_leading_padding_ms: int = 20
    number_trim_trailing_padding_ms: int = 55
    number_symbol_pause_ms: int = 120
    client_calls_interval_seconds: float = 5.0
    client_calls_repeat_enabled: bool = False
    client_calls_repeat_interval_seconds: float = 3.0
    client_calls_repeat_notification_enabled: bool = False
    client_calls_text_voice: str = ""
    client_calls_text_voice_id: str = ""
    client_calls_text_language_code: str = ""
    employees_file_path: str = ""
    generator_api_key: str = ""
    generator_selected_device: str = ""
    generator_volume: float = 0.8
    generator_master_volume: int = 100
    generator_language_code: str = "ru-RU"
    generator_accent_code: str = ""
    generator_speed: int = 0
    generator_voice: str = ""
    generator_voice_id: str = ""
    main_window_geometry: str = ""


@dataclass
class ClientCall:
    START_LABELS: ClassVar[dict[str, str]] = {
        "1": "Клиент с авто",
    }
    END_LABELS: ClassVar[dict[str, str]] = {
        "1": "пожалуйста, пройдите к своему авто",
        "2": "пожалуйста, пройдите в приёмку",
    }

    start_choice: str
    car_number: str
    end_choice: str
    display_message: str = ""
    is_text_message: bool = False
    speech_text_override: str = ""
    audio_file_path: str = ""
    call_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.call_id:
            self.call_id = str(uuid.uuid4())

    @property
    def display_text(self) -> str:
        if self.display_message:
            return self.display_message

        start_label = self.START_LABELS.get(str(self.start_choice).strip(), f"Начало {self.start_choice}")
        end_label = self.END_LABELS.get(str(self.end_choice).strip(), f"Концовка {self.end_choice}")
        return f"{start_label} {self.car_number.upper()}, {end_label}"

    @property
    def speech_text(self) -> str:
        return self.speech_text_override or self.display_text
