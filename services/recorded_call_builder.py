import os
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf


class RecordedCallBuilderService:
    def __init__(self) -> None:
        self.audio_root = self._resolve_audio_root()

    def build_display_text(self, start_choice: str, car_number: str, end_choice: str) -> str:
        return f"start_{start_choice} {car_number.upper()} end_{end_choice}"

    def build_audio_file(
        self,
        start_choice: str,
        car_number: str,
        end_choice: str,
        playback_rate: float = 1.0,
    ) -> str:
        audio_paths = self.construct_message(start_choice, car_number, end_choice)
        chunks: list[np.ndarray] = []
        sample_rate: int | None = None

        for audio_path in audio_paths:
            data, current_sample_rate = sf.read(audio_path, dtype="float32", always_2d=True)
            if data.shape[1] > 2:
                data = data[:, :2]

            if sample_rate is None:
                sample_rate = current_sample_rate
            elif current_sample_rate != sample_rate:
                raise RuntimeError(f"Разная частота дискретизации у файлов вызова: {audio_path}")

            chunks.append(data)

        if not chunks or sample_rate is None:
            raise RuntimeError("Не удалось собрать аудио вызова")

        merged_audio = np.concatenate(chunks, axis=0)
        temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(temp_fd)
        stretched_audio = self._time_stretch_audio(merged_audio, playback_rate)
        sf.write(temp_path, stretched_audio, sample_rate)
        return temp_path

    def construct_message(self, start_choice: str, car_number: str, end_choice: str) -> list[str]:
        start_audio = self._audio_path("start_options", f"start_{start_choice}")
        car_audio_files: list[str] = []
        normalized_number = car_number.lower()

        for index, symbol in enumerate(normalized_number):
            digit_prefix = "digit_"
            if symbol.isdigit():
                if index == 1:
                    car_audio_files.append(self._audio_path("digits", f"{digit_prefix}{symbol}00"))
                elif index == 2 and int(symbol) <= 1:
                    continue
                elif index == 3 and normalized_number[index - 1] == "1":
                    car_audio_files.append(self._audio_path("digits", f"{digit_prefix}1{symbol}"))
                    continue
                elif index == 3 and symbol == "0":
                    continue
                elif index == 2:
                    car_audio_files.append(self._audio_path("digits", f"{digit_prefix}{symbol}0"))
                elif len(normalized_number) == 8 and index == 6 and int(symbol) == 1:
                    continue
                elif len(normalized_number) == 8 and index == 7 and normalized_number[index - 1] == "1":
                    car_audio_files.append(self._audio_path("digits", f"{digit_prefix}1{symbol}"))
                    continue
                elif len(normalized_number) == 8 and index == 7 and symbol == "0":
                    continue
                elif len(normalized_number) == 8 and index == 6:
                    car_audio_files.append(self._audio_path("digits", f"{digit_prefix}{symbol}0"))
                elif len(normalized_number) == 9 and index == 6:
                    car_audio_files.append(self._audio_path("digits", f"{digit_prefix}{symbol}00"))
                elif len(normalized_number) == 9 and index == 7 and int(symbol) == 1:
                    continue
                elif len(normalized_number) == 9 and index == 8 and normalized_number[index - 1] == "1":
                    car_audio_files.append(self._audio_path("digits", f"{digit_prefix}1{symbol}"))
                    continue
                elif len(normalized_number) == 9 and index == 8 and symbol == "0":
                    continue
                elif len(normalized_number) == 9 and index == 7:
                    car_audio_files.append(self._audio_path("digits", f"{digit_prefix}{symbol}0"))
                else:
                    car_audio_files.append(self._audio_path("digits", f"{digit_prefix}{symbol}"))
            else:
                car_audio_files.append(self._audio_path("lettrs", f"lettr_{symbol}"))

        end_audio = self._audio_path("end_options", f"end_{end_choice}")
        return [start_audio] + car_audio_files + [end_audio]

    def _audio_path(self, folder: str, stem: str) -> str:
        for suffix in (".wav", ".mp3"):
            candidate = self.audio_root / folder / f"{stem}{suffix}"
            if candidate.exists():
                return str(candidate)
        raise FileNotFoundError(f"Не найден аудиофайл: {folder}/{stem}")

    def _resolve_audio_root(self) -> Path:
        candidates = [
            Path.cwd() / "audio",
            Path(__file__).resolve().parent.parent / "audio",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _time_stretch_audio(self, audio: np.ndarray, playback_rate: float) -> np.ndarray:
        rate = max(playback_rate, 0.1)
        if abs(rate - 1.0) < 1e-3:
            return audio

        channels = [
            self._time_stretch_channel(audio[:, channel], rate)
            for channel in range(audio.shape[1])
        ]
        min_length = min(len(channel) for channel in channels)
        return np.column_stack([channel[:min_length] for channel in channels]).astype("float32")

    def _time_stretch_channel(self, audio: np.ndarray, rate: float) -> np.ndarray:
        frame_length = 2048
        hop_length = frame_length // 4
        if len(audio) < frame_length:
            return audio.astype("float32")

        stft_matrix = self._stft(audio, frame_length, hop_length)
        stretched_stft = self._phase_vocoder(stft_matrix, rate, hop_length)
        stretched_audio = self._istft(stretched_stft, hop_length, len(audio), rate)
        return np.clip(stretched_audio, -1.0, 1.0).astype("float32")

    def _stft(self, audio: np.ndarray, frame_length: int, hop_length: int) -> np.ndarray:
        window = np.hanning(frame_length).astype("float32")
        padded = np.pad(audio, (frame_length // 2, frame_length // 2))
        frame_count = 1 + max(0, (len(padded) - frame_length) // hop_length)
        frames = np.empty((frame_length // 2 + 1, frame_count), dtype=np.complex64)

        for index in range(frame_count):
            start = index * hop_length
            frame = padded[start:start + frame_length]
            frames[:, index] = np.fft.rfft(frame * window)

        return frames

    def _phase_vocoder(self, stft_matrix: np.ndarray, rate: float, hop_length: int) -> np.ndarray:
        time_steps = np.arange(0, stft_matrix.shape[1], rate, dtype=np.float64)
        if len(time_steps) == 0:
            return stft_matrix[:, :1]

        phase_advance = np.linspace(0, np.pi * hop_length, stft_matrix.shape[0])
        output = np.zeros((stft_matrix.shape[0], len(time_steps)), dtype=np.complex64)

        phase = np.angle(stft_matrix[:, 0])
        last_phase = phase.copy()

        for output_index, step in enumerate(time_steps):
            frame_index = min(int(step), stft_matrix.shape[1] - 2)
            alpha = step - frame_index

            left = stft_matrix[:, frame_index]
            right = stft_matrix[:, frame_index + 1]

            magnitude = (1.0 - alpha) * np.abs(left) + alpha * np.abs(right)

            current_phase = np.angle(right)
            delta = current_phase - last_phase - phase_advance
            delta -= 2.0 * np.pi * np.round(delta / (2.0 * np.pi))
            phase += phase_advance + delta
            last_phase = current_phase

            output[:, output_index] = magnitude * np.exp(1j * phase)

        return output

    def _istft(
        self,
        stft_matrix: np.ndarray,
        hop_length: int,
        original_length: int,
        rate: float,
    ) -> np.ndarray:
        frame_length = (stft_matrix.shape[0] - 1) * 2
        window = np.hanning(frame_length).astype("float32")
        expected_length = int(round(original_length / rate)) + frame_length
        overlap_length = hop_length * max(0, stft_matrix.shape[1] - 1) + frame_length
        output_length = max(expected_length, overlap_length)
        output = np.zeros(output_length, dtype=np.float32)
        window_sums = np.zeros(output_length, dtype=np.float32)

        for index in range(stft_matrix.shape[1]):
            start = index * hop_length
            frame = np.fft.irfft(stft_matrix[:, index]).astype("float32")
            output[start:start + frame_length] += frame * window
            window_sums[start:start + frame_length] += window ** 2

        nonzero = window_sums > 1e-8
        output[nonzero] /= window_sums[nonzero]

        trim = frame_length // 2
        output = output[trim:-trim] if len(output) > trim * 2 else output
        target_length = max(1, int(round(original_length / rate)))
        return output[:target_length]
