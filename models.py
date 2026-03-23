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
    client_calls_selected_device: str = ""
    client_calls_volume: float = 0.8
    client_calls_speech_rate: float = 1.0
    client_calls_interval_seconds: float = 5.0
    main_window_geometry: str = ""
    scheduler_weekdays: list[int] = field(default_factory=lambda: [0, 1, 2, 3, 4, 5, 6])


@dataclass
class ClientCall:
    counter: str
    ticket: str
    speech_message: str = ""
    call_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.call_id:
            self.call_id = str(uuid.uuid4())

    @property
    def display_text(self) -> str:
        return self.speech_text

    @property
    def speech_text(self) -> str:
        return self.speech_message or f"Клиент {self.ticket}. Подойдите к окну {self.counter}."
