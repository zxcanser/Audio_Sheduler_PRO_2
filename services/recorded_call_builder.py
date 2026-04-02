import os
import re
import tempfile
import unicodedata
from pathlib import Path

import numpy as np
import soundfile as sf


class RecordedCallBuilderService:
    NUMBER_SEGMENT_FADE_SECONDS = 0.012

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
        repeat_count: int = 1,
        pause_seconds: float = 0.0,
    ) -> str:
        audio_segments = self.construct_message(start_choice, car_number, end_choice)
        chunks: list[np.ndarray] = []
        sample_rate: int | None = None

        for index, (audio_path, is_number_segment) in enumerate(audio_segments):
            data, current_sample_rate = sf.read(audio_path, dtype="float32", always_2d=True)
            if data.shape[1] > 2:
                data = data[:, :2]
            if data.shape[1] == 1:
                data = np.repeat(data, 2, axis=1)

            if sample_rate is None:
                sample_rate = current_sample_rate
            elif current_sample_rate != sample_rate:
                raise RuntimeError(f"Разная частота дискретизации у файлов вызова: {audio_path}")

            if is_number_segment:
                data = self._time_stretch_audio(data, playback_rate)
                data = self._apply_fade(data, current_sample_rate, self.NUMBER_SEGMENT_FADE_SECONDS)

            chunks.append(data)
            next_is_number_segment = index + 1 < len(audio_segments) and audio_segments[index + 1][1]
            if is_number_segment and next_is_number_segment:
                pause_chunk = self._build_number_pause(current_sample_rate, data.shape[1], playback_rate)
                if pause_chunk is not None:
                    chunks.append(pause_chunk)

        if not chunks or sample_rate is None:
            raise RuntimeError("Не удалось собрать аудио вызова")

        merged_audio = np.concatenate(chunks, axis=0)
        if repeat_count > 1:
            merged_audio = self._repeat_audio_with_pause(
                merged_audio,
                sample_rate,
                repeat_count=repeat_count,
                pause_seconds=pause_seconds,
            )
        temp_fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(temp_fd)
        sf.write(temp_path, merged_audio, sample_rate)
        return temp_path

    def should_repeat_car_call(self, car_number: str) -> bool:
        normalized_value = (car_number or "").strip()
        if not normalized_value:
            return False
        if self._worker_audio_path(normalized_value) is not None:
            return False
        return any(symbol.isdigit() for symbol in normalized_value)

    def get_worker_audio_path(self, worker_name: str) -> str | None:
        return self._worker_audio_path(worker_name)

    def construct_message(self, start_choice: str, car_number: str, end_choice: str) -> list[tuple[str, bool]]:
        start_audio = self._audio_path("start_options", f"start_{start_choice}")
        audio_segments: list[tuple[str, bool]] = [(start_audio, False)]
        normalized_number = car_number.lower().strip()

        worker_audio = self._worker_audio_path(car_number)
        if worker_audio is not None:
            end_audio = self._audio_path("end_options", f"end_{end_choice}")
            return [(start_audio, False), (worker_audio, False), (end_audio, False)]

        for chunk in re.findall(r"\d+|[^\d]+", normalized_number):
            if chunk.isdigit():
                audio_segments.extend((audio_path, True) for audio_path in self._build_number_audio(chunk))
                continue

            for symbol in chunk:
                if symbol.isspace():
                    continue
                audio_segments.append((self._audio_path("lettrs", f"lettr_{symbol}"), True))

        end_audio = self._audio_path("end_options", f"end_{end_choice}")
        audio_segments.append((end_audio, False))
        return audio_segments

    def _build_number_audio(self, value: str) -> list[str]:
        if not value:
            return []

        if len(value) == 1:
            return [self._digit_audio(value)]

        if len(value) == 2:
            return self._build_two_digit_audio(value)

        if len(value) == 3:
            hundreds = value[0]
            remainder = value[1:]
            audio_files: list[str] = []

            if hundreds == "0":
                audio_files.append(self._digit_audio("0"))
            else:
                audio_files.append(self._audio_path("digits", f"digit_{hundreds}00"))

            if remainder != "00":
                if hundreds != "0" and remainder.startswith("0"):
                    audio_files.append(self._digit_audio(remainder[1]))
                else:
                    audio_files.extend(self._build_two_digit_audio(remainder))
            return audio_files

        audio_files: list[str] = []
        for symbol in value:
            audio_files.append(self._digit_audio(symbol))
        return audio_files

    def _build_two_digit_audio(self, value: str) -> list[str]:
        number = int(value)
        if number == 0:
            return [self._digit_audio("0")]
        if value.startswith("0"):
            return [self._digit_audio("0"), self._digit_audio(value[1])]
        if 10 <= number <= 19:
            return [self._audio_path("digits", f"digit_{number}")]

        audio_files: list[str] = []
        tens = (number // 10) * 10
        units = number % 10

        if tens > 0:
            audio_files.append(self._audio_path("digits", f"digit_{tens}"))
        if units > 0:
            audio_files.append(self._audio_path("digits", f"digit_{units}"))
        return audio_files

    def _digit_audio(self, value: str) -> str:
        if value == "0":
            return self._audio_path("digits", "digit_00")
        return self._audio_path("digits", f"digit_{value}")

    def _audio_path(self, folder: str, stem: str) -> str:
        for suffix in (".wav", ".mp3"):
            candidate = self.audio_root / folder / f"{stem}{suffix}"
            if candidate.exists():
                return str(candidate)
        raise FileNotFoundError(f"Не найден аудиофайл: {folder}/{stem}")

    def _worker_audio_path(self, worker_name: str) -> str | None:
        workers_dir = self.audio_root / "workers"
        if not workers_dir.exists():
            return None

        normalized_name = self._normalize_worker_name(worker_name)
        if not normalized_name:
            return None

        direct_candidates = [
            workers_dir / f"{normalized_name}.mp3",
            workers_dir / f"{normalized_name}.wav",
        ]
        for candidate in direct_candidates:
            if candidate.exists():
                return str(candidate)

        for candidate in workers_dir.iterdir():
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in {".mp3", ".wav"}:
                continue
            if self._normalize_worker_name(candidate.stem) == normalized_name:
                return str(candidate)

        return None

    def _normalize_worker_name(self, value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).strip()
        normalized = re.sub(r"\s+", "_", normalized)
        return normalized.casefold()

    def _build_number_pause(self, sample_rate: int, channels: int, playback_rate: float) -> np.ndarray | None:
        rate = max(playback_rate, 0.1)
        pause_seconds = 0.18 / (rate ** 1.8)
        frame_count = max(0, int(round(sample_rate * pause_seconds)))
        if frame_count <= 0:
            return None
        return np.zeros((frame_count, channels), dtype="float32")

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

        effective_rate = 1.0 + (rate - 1.0) * 0.45
        channels = [
            self._time_stretch_channel(audio[:, channel], effective_rate)
            for channel in range(audio.shape[1])
        ]
        min_length = min(len(channel) for channel in channels)
        return np.column_stack([channel[:min_length] for channel in channels]).astype("float32")

    def _apply_fade(self, audio: np.ndarray, sample_rate: int, fade_seconds: float) -> np.ndarray:
        frame_count = len(audio)
        if frame_count == 0:
            return audio

        fade_frames = min(int(round(sample_rate * max(fade_seconds, 0.0))), frame_count // 2)
        if fade_frames <= 1:
            return audio

        result = audio.copy()
        fade_in = np.linspace(0.0, 1.0, fade_frames, dtype=np.float32)
        fade_out = np.linspace(1.0, 0.0, fade_frames, dtype=np.float32)
        result[:fade_frames] *= fade_in[:, None]
        result[-fade_frames:] *= fade_out[:, None]
        return result

    def _repeat_audio_with_pause(
        self,
        audio: np.ndarray,
        sample_rate: int,
        repeat_count: int,
        pause_seconds: float,
    ) -> np.ndarray:
        if repeat_count <= 1:
            return audio

        segments: list[np.ndarray] = []
        silence_frames = max(0, int(round(sample_rate * max(pause_seconds, 0.0))))
        silence = np.zeros((silence_frames, audio.shape[1]), dtype="float32") if silence_frames else None

        for index in range(repeat_count):
            segments.append(audio)
            if silence is not None and index < repeat_count - 1:
                segments.append(silence)

        return np.concatenate(segments, axis=0)

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
