import os
import uuid
from dataclasses import dataclass, field
from typing import Optional


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
    client_calls_voice_message_file_path: str = ""
    client_calls_selected_device: str = ""
    client_calls_voice_message_selected_device: str = ""
    client_calls_volume: float = 0.8
    client_calls_voice_message_volume: float = 1.0
    client_calls_speech_rate: float = 1.0
    client_calls_interval_seconds: float = 5.0
    client_calls_repeat_enabled: bool = False
    client_calls_repeat_interval_seconds: float = 3.0
    client_calls_repeat_notification_enabled: bool = False
    client_calls_text_voice: str = ""
    client_calls_text_voice_id: str = ""
    client_calls_text_language_code: str = ""
    employees_file_path: str = ""
    generator_api_file_path: str = ""
    generator_selected_device: str = ""
    generator_volume: float = 0.8
    generator_language_code: str = "ru-RU"
    generator_voice: str = ""
    generator_voice_id: str = ""
    main_window_geometry: str = ""
    scheduler_weekdays: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])


@dataclass
class ClientCall:
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
        return self.display_message or f"start_{self.start_choice} {self.car_number.upper()} end_{self.end_choice}"

    @property
    def speech_text(self) -> str:
        return self.speech_text_override or self.display_text
