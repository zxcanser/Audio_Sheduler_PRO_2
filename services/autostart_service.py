import os
import platform
import plistlib
import subprocess
import sys
from pathlib import Path


class AutostartService:
    MACOS_LABEL = "com.audio_scheduler_pro.autostart"
    WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
    WINDOWS_VALUE_NAME = "AudioSchedulerPro"

    def __init__(self) -> None:
        self.platform = platform.system()

    def set_enabled(self, enabled: bool) -> None:
        if self.platform == "Darwin":
            self._set_enabled_macos(enabled)
            return
        if self.platform == "Windows":
            self._set_enabled_windows(enabled)
            return
        raise RuntimeError("Автозапуск поддерживается только на macOS и Windows")

    def _set_enabled_macos(self, enabled: bool) -> None:
        plist_path = self._macos_plist_path()
        if enabled:
            plist_path.parent.mkdir(parents=True, exist_ok=True)
            with plist_path.open("wb") as plist_file:
                plistlib.dump(self._build_macos_plist(), plist_file)
        elif plist_path.exists():
            plist_path.unlink()

    def _build_macos_plist(self) -> dict:
        executable_command = self._build_launch_command()
        return {
            "Label": self.MACOS_LABEL,
            "ProgramArguments": executable_command,
            "RunAtLoad": True,
            "KeepAlive": False,
            "WorkingDirectory": str(self._application_dir()),
        }

    def _macos_plist_path(self) -> Path:
        return Path.home() / "Library" / "LaunchAgents" / f"{self.MACOS_LABEL}.plist"

    def _set_enabled_windows(self, enabled: bool) -> None:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            self.WINDOWS_RUN_KEY,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, self.WINDOWS_VALUE_NAME, 0, winreg.REG_SZ, self._build_windows_command())
            else:
                try:
                    winreg.DeleteValue(key, self.WINDOWS_VALUE_NAME)
                except FileNotFoundError:
                    pass

    def _build_launch_command(self) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable]

        main_path = self._application_dir() / "main.py"
        return [sys.executable, str(main_path)]

    def _build_windows_command(self) -> str:
        command = self._build_launch_command()
        return subprocess.list2cmdline(command)

    def _application_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent.parent
