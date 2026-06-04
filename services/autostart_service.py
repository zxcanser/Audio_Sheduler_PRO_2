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
    WINDOWS_LEGACY_VALUE_NAMES = ("Audio Scheduler PRO", "AudioSchedulerPRO")
    WINDOWS_STARTUP_SCRIPT_NAME = "AudioSchedulerPro.vbs"
    WINDOWS_LEGACY_STARTUP_FILE_NAMES = (
        "AudioSchedulerPro.lnk",
        "Audio Scheduler PRO.lnk",
        "AudioSchedulerPRO.lnk",
        "AudioSchedulerPro.cmd",
        "Audio Scheduler PRO.cmd",
        "AudioSchedulerPRO.cmd",
    )

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

    def is_enabled(self) -> bool:
        if self.platform == "Darwin":
            return self._macos_plist_path().exists()
        if self.platform == "Windows":
            return self._is_enabled_windows()
        return False

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
        if enabled:
            self._write_windows_startup_script()
            self._delete_windows_registry_values()
            self._delete_legacy_windows_startup_files()
        else:
            self._delete_windows_registry_values()
            self._delete_windows_startup_files()

    def _is_enabled_windows(self) -> bool:
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.WINDOWS_RUN_KEY,
                0,
                winreg.KEY_QUERY_VALUE,
            ) as key:
                has_registry_autostart = any(
                    self._windows_value_exists(key, value_name) for value_name in self._windows_value_names()
                )
        except FileNotFoundError:
            has_registry_autostart = False

        return has_registry_autostart or self._has_windows_startup_shortcut()

    def _windows_value_exists(self, key, value_name: str) -> bool:
        import winreg

        try:
            value, _ = winreg.QueryValueEx(key, value_name)
        except FileNotFoundError:
            return False
        return bool(str(value).strip())

    def _windows_value_names(self) -> tuple[str, ...]:
        return (self.WINDOWS_VALUE_NAME, *self.WINDOWS_LEGACY_VALUE_NAMES)

    def _has_windows_startup_shortcut(self) -> bool:
        return any(path.exists() for path in self._windows_startup_file_paths())

    def _write_windows_startup_script(self) -> None:
        startup_dir = self._windows_startup_dir()
        startup_dir.mkdir(parents=True, exist_ok=True)
        self._windows_startup_script_path().write_text(self._build_windows_startup_script(), encoding="utf-8")

    def _build_windows_startup_script(self) -> str:
        working_dir = self._vbscript_string(str(self._application_dir()))
        command = self._vbscript_string(self._build_windows_command())
        return (
            'Set WshShell = CreateObject("WScript.Shell")\n'
            f'WshShell.CurrentDirectory = "{working_dir}"\n'
            f'WshShell.Run "{command}", 0, False\n'
        )

    def _delete_windows_registry_values(self) -> None:
        import winreg

        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.WINDOWS_RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            )
        except FileNotFoundError:
            return

        with key:
            for value_name in self._windows_value_names():
                try:
                    winreg.DeleteValue(key, value_name)
                except FileNotFoundError:
                    pass

    def _delete_windows_startup_files(self) -> None:
        for path in self._windows_startup_file_paths():
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def _delete_legacy_windows_startup_files(self) -> None:
        for path in self._legacy_windows_startup_file_paths():
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def _windows_startup_file_paths(self) -> list[Path]:
        return [self._windows_startup_script_path(), *self._legacy_windows_startup_file_paths()]

    def _legacy_windows_startup_file_paths(self) -> list[Path]:
        startup_dir = self._windows_startup_dir()
        return [startup_dir / file_name for file_name in self.WINDOWS_LEGACY_STARTUP_FILE_NAMES]

    def _windows_startup_script_path(self) -> Path:
        return self._windows_startup_dir() / self.WINDOWS_STARTUP_SCRIPT_NAME

    def _windows_startup_dir(self) -> Path:
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    def _build_launch_command(self) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable]

        main_path = self._application_dir() / "main.py"
        python_executable = Path(sys.executable)
        if self.platform == "Windows":
            pythonw_executable = python_executable.with_name("pythonw.exe")
            if pythonw_executable.exists():
                python_executable = pythonw_executable
        return [str(python_executable), str(main_path)]

    def _build_windows_command(self) -> str:
        command = self._build_launch_command()
        return subprocess.list2cmdline(command)

    def _vbscript_string(self, value: str) -> str:
        return value.replace('"', '""')

    def _application_dir(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent.parent
