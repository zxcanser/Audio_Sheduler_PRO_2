import os
import uuid
from dataclasses import dataclass
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
    client_calls_file_path: str = ""
    client_calls_selected_device: str = ""
    client_calls_volume: float = 0.8
    client_calls_interval_seconds: float = 5.0


@dataclass
class ClientCall:
    counter: str
    ticket: str
    call_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.call_id:
            self.call_id = str(uuid.uuid4())

    @property
    def display_text(self) -> str:
        return f"Окно {self.counter} | {self.ticket}"

    @property
    def speech_text(self) -> str:
        return f"Клиент {self.ticket}. Подойдите к окну {self.counter}."
