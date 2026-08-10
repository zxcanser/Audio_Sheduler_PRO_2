import os
import platform
import sys
from pathlib import Path


APP_NAME = "AudioSchedulerPro"
APP_VERSION = "2.3.3"
WINDOW_TITLE = "Audio Scheduler PRO - система оповещений"
APP_ROOT_DIR = Path(__file__).resolve().parent
APP_ICON_FILE = str(APP_ROOT_DIR / "ASP_icon.ico")
GITHUB_RELEASES_API_URL = "https://api.github.com/repos/zxcanser/Audio_Sheduler_PRO_2/releases/latest"


def _get_app_data_dir() -> Path:
    system = platform.system()
    if system == "Windows":
        base_dir = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base_dir / APP_NAME
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def _get_legacy_base_dirs() -> list[Path]:
    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parent,
    ]
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent)

    unique_dirs: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_dirs.append(resolved)
    return unique_dirs


APP_DATA_DIR = _get_app_data_dir()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = str(APP_DATA_DIR / "config.json")
SCHEDULE_FILE = str(APP_DATA_DIR / "schedule.json")
CLIENT_CALLS_LOG_FILE = str(APP_DATA_DIR / "client_calls.log")
ERROR_LOG_FILE = str(APP_DATA_DIR / "error.log")
INSTANCE_LOCK_FILE = str(APP_DATA_DIR / "app.lock")
WORKDAY_CALENDAR_CACHE_FILE = str(APP_DATA_DIR / "workday_calendar_cache.json")

LEGACY_CONFIG_FILES = [str(base_dir / "config.json") for base_dir in _get_legacy_base_dirs()]
LEGACY_SCHEDULE_FILES = [str(base_dir / "schedule.json") for base_dir in _get_legacy_base_dirs()]
