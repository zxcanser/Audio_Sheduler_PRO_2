import os
import platform
import subprocess
import tempfile


class SpeechSynthesizerService:
    DEFAULT_MACOS_RATE = 175

    def __init__(self) -> None:
        self.platform = platform.system()

    def synthesize_to_file(self, text: str, speech_rate: float = 1.0) -> str:
        temp_fd, temp_path = tempfile.mkstemp(suffix=self._file_suffix())
        os.close(temp_fd)

        try:
            if self.platform == "Darwin":
                self._synthesize_macos(text, temp_path, speech_rate)
            elif self.platform == "Windows":
                self._synthesize_windows(text, temp_path, speech_rate)
            else:
                raise RuntimeError("Озвучка вызовов поддерживается только на macOS и Windows")
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

        return temp_path

    def _file_suffix(self) -> str:
        return ".wav" if self.platform == "Windows" else ".aiff"

    def _synthesize_macos(self, text: str, output_path: str, speech_rate: float) -> None:
        rate = max(90, min(360, int(round(self.DEFAULT_MACOS_RATE * speech_rate))))
        subprocess.run(
            ["say", "-r", str(rate), "-o", output_path, text],
            check=True,
            capture_output=True,
            text=True,
        )

    def _synthesize_windows(self, text: str, output_path: str, speech_rate: float) -> None:
        escaped_text = text.replace("'", "''")
        escaped_path = output_path.replace("'", "''")
        rate = max(-10, min(10, int(round((speech_rate - 1.0) * 10))))
        command = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {rate}; "
            f"$s.SetOutputToWaveFile('{escaped_path}'); "
            f"$s.Speak('{escaped_text}'); "
            "$s.Dispose();"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            check=True,
            capture_output=True,
            text=True,
        )
