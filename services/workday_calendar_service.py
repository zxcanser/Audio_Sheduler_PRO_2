from datetime import date, timedelta
import json
import threading
import urllib.error
import urllib.request

from config import WORKDAY_CALENDAR_CACHE_FILE


class WorkdayCalendarService:
    BASE_URL = "https://isdayoff.ru"
    FALLBACK_BASE_URL = "http://isdayoff.ru"
    WORKDAY = 0
    DAY_OFF = 1
    SHORTENED_WORKDAY = 2

    def __init__(self) -> None:
        self._year_cache: dict[int, dict[date, int]] = {}
        self._lock = threading.Lock()
        self._load_cache_from_disk()

    def get_day_status(self, target_date: date) -> int:
        return self.get_year_statuses(target_date.year)[target_date]

    def get_cached_day_status(self, target_date: date) -> int | None:
        with self._lock:
            return self._year_cache.get(target_date.year, {}).get(target_date)

    def get_offline_day_status(self, target_date: date) -> int:
        cached_status = self.get_cached_day_status(target_date)
        if cached_status is not None:
            return cached_status
        return self.get_fallback_day_status(target_date)

    def get_year_statuses(self, year: int) -> dict[date, int]:
        with self._lock:
            cached_statuses = self._year_cache.get(year)
            if cached_statuses is not None:
                return cached_statuses.copy()

        statuses = self._fetch_year_statuses(year)
        with self._lock:
            self._year_cache[year] = statuses
            self._save_cache_to_disk_locked()
        return statuses.copy()

    def get_cached_year_statuses(self, year: int) -> dict[date, int] | None:
        with self._lock:
            statuses = self._year_cache.get(year)
            if statuses is None:
                return None
            return statuses.copy()

    def get_fallback_day_status(self, target_date: date) -> int:
        return self.DAY_OFF if target_date.weekday() >= 5 else self.WORKDAY

    def get_fallback_year_statuses(self, year: int) -> dict[date, int]:
        first_day = date(year, 1, 1)
        days_count = (date(year + 1, 1, 1) - first_day).days
        return {
            first_day + timedelta(days=index): self.get_fallback_day_status(first_day + timedelta(days=index))
            for index in range(days_count)
        }

    def is_workday_status(self, status: int | None) -> bool:
        return status in {self.WORKDAY, self.SHORTENED_WORKDAY}

    def _fetch_year_statuses(self, year: int) -> dict[date, int]:
        raw_data = self._fetch_year_data(year)

        if not raw_data or any(symbol not in {"0", "1", "2"} for symbol in raw_data):
            raise RuntimeError("Сервис производственного календаря вернул некорректный ответ")

        first_day = date(year, 1, 1)
        statuses: dict[date, int] = {}
        for index, symbol in enumerate(raw_data):
            current_day = first_day + timedelta(days=index)
            if current_day.year != year:
                break
            statuses[current_day] = int(symbol)

        expected_days = (date(year + 1, 1, 1) - first_day).days
        if len(statuses) != expected_days:
            raise RuntimeError("Сервис производственного календаря вернул неполный год")

        return statuses

    def _fetch_year_data(self, year: int) -> str:
        primary_url = f"{self.BASE_URL}/api/getdata?year={year}"
        try:
            return self._read_url(primary_url)
        except urllib.error.URLError as primary_error:
            fallback_url = f"{self.FALLBACK_BASE_URL}/api/getdata?year={year}"
            try:
                return self._read_url(fallback_url)
            except urllib.error.URLError as fallback_error:
                reason = getattr(fallback_error, "reason", fallback_error)
                if reason == fallback_error:
                    reason = getattr(primary_error, "reason", primary_error)
                raise RuntimeError(f"Не удалось получить производственный календарь: {reason}") from fallback_error

    def _read_url(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"User-Agent": "AudioSchedulerPro/1.0"})
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.read().decode("utf-8").strip()

    def _load_cache_from_disk(self) -> None:
        try:
            with open(WORKDAY_CALENDAR_CACHE_FILE, "r", encoding="utf-8") as cache_file:
                raw_cache = json.load(cache_file)
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return

        if not isinstance(raw_cache, dict):
            return

        loaded_cache: dict[int, dict[date, int]] = {}
        for year_text, year_data in raw_cache.items():
            try:
                year = int(year_text)
            except (TypeError, ValueError):
                continue
            if not isinstance(year_data, str):
                continue

            statuses = self._parse_year_statuses(year, year_data)
            if statuses:
                loaded_cache[year] = statuses

        with self._lock:
            self._year_cache.update(loaded_cache)

    def _save_cache_to_disk_locked(self) -> None:
        serialized_cache: dict[str, str] = {}
        for year, statuses in self._year_cache.items():
            first_day = date(year, 1, 1)
            expected_days = (date(year + 1, 1, 1) - first_day).days
            year_values = []
            for index in range(expected_days):
                current_day = first_day + timedelta(days=index)
                status = statuses.get(current_day)
                if status not in {self.WORKDAY, self.DAY_OFF, self.SHORTENED_WORKDAY}:
                    break
                year_values.append(str(status))
            if len(year_values) == expected_days:
                serialized_cache[str(year)] = "".join(year_values)

        try:
            with open(WORKDAY_CALENDAR_CACHE_FILE, "w", encoding="utf-8") as cache_file:
                json.dump(serialized_cache, cache_file, ensure_ascii=False, indent=2)
        except OSError:
            return

    def _parse_year_statuses(self, year: int, raw_data: str) -> dict[date, int]:
        if not raw_data or any(symbol not in {"0", "1", "2"} for symbol in raw_data):
            return {}

        first_day = date(year, 1, 1)
        expected_days = (date(year + 1, 1, 1) - first_day).days
        if len(raw_data) != expected_days:
            return {}

        return {
            first_day + timedelta(days=index): int(symbol)
            for index, symbol in enumerate(raw_data)
        }
