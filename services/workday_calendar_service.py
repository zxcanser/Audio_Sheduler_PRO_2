from datetime import date, timedelta
import threading
import urllib.error
import urllib.request


class WorkdayCalendarService:
    BASE_URL = "https://isdayoff.ru"
    FALLBACK_BASE_URL = "http://isdayoff.ru"
    WORKDAY = 0
    DAY_OFF = 1
    SHORTENED_WORKDAY = 2

    def __init__(self) -> None:
        self._year_cache: dict[int, dict[date, int]] = {}
        self._lock = threading.Lock()

    def get_day_status(self, target_date: date) -> int:
        return self.get_year_statuses(target_date.year)[target_date]

    def get_cached_day_status(self, target_date: date) -> int | None:
        with self._lock:
            return self._year_cache.get(target_date.year, {}).get(target_date)

    def get_year_statuses(self, year: int) -> dict[date, int]:
        with self._lock:
            cached_statuses = self._year_cache.get(year)
            if cached_statuses is not None:
                return cached_statuses.copy()

        statuses = self._fetch_year_statuses(year)
        with self._lock:
            self._year_cache[year] = statuses
        return statuses.copy()

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
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8").strip()
