from typing import List, Optional

from models import ScheduleEntry
from services.validation_service import ValidationError


class ScheduleManager:
    def __init__(self, entries: Optional[List[ScheduleEntry]] = None):
        self._entries: List[ScheduleEntry] = entries[:] if entries else []

    def get_all(self) -> List[ScheduleEntry]:
        return sorted(self._entries, key=lambda x: (x.time_str, x.file_name.lower()))

    def add_entry(self, time_str: str, file_path: str) -> ScheduleEntry:
        if self._is_duplicate(time_str, file_path):
            raise ValidationError("Такая запись уже существует")

        entry = ScheduleEntry(time_str=time_str, file_path=file_path)
        self._entries.append(entry)
        return entry

    def delete_entry(self, entry_id: str) -> None:
        self._entries = [e for e in self._entries if e.entry_id != entry_id]

    def get_by_id(self, entry_id: str) -> Optional[ScheduleEntry]:
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def _is_duplicate(self, time_str: str, file_path: str, ignore_entry_id: Optional[str] = None) -> bool:
        for entry in self._entries:
            if ignore_entry_id and entry.entry_id == ignore_entry_id:
                continue
            if entry.time_str == time_str and entry.file_path == file_path:
                return True
        return False
