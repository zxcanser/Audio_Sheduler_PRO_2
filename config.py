import os
import platform
import sys
from pathlib import Path


APP_NAME = "AudioSchedulerPro"
WINDOW_TITLE = "Audio Scheduler PRO - система оповещений"


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

LEGACY_CONFIG_FILES = [str(base_dir / "config.json") for base_dir in _get_legacy_base_dirs()]
LEGACY_SCHEDULE_FILES = [str(base_dir / "schedule.json") for base_dir in _get_legacy_base_dirs()]
