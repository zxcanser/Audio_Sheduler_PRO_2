import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass

try:
    import certifi
except ImportError:
    certifi = None


@dataclass(frozen=True)
class VoiceMakerLanguage:
    label: str
    code: str


@dataclass(frozen=True)
class VoiceMakerVoice:
    label: str
    voice_id: str
    language_code: str
    language_name: str = ""
    engine: str = ""

    @property
    def supports_accent_code(self) -> bool:
        normalized_voice_id = self.voice_id.lower()
        normalized_engine = self.engine.lower()
        return (
            normalized_voice_id.startswith("ai1-")
            or normalized_voice_id.startswith("pro1-")
            or normalized_voice_id.startswith("pro2-")
            or normalized_engine in {"ai1", "pro1", "pro2"}
        )


class VoiceMakerService:
    VOICE_LIST_URL = "https://developer.voicemaker.in/api/v1/voice/list"
    CONVERT_URL = "https://developer.voicemaker.in/api/v1/voice/convert"

    LANGUAGES: list[VoiceMakerLanguage] = [
        VoiceMakerLanguage("Русский", "ru-RU"),
        VoiceMakerLanguage("Английский (США)", "en-US"),
        VoiceMakerLanguage("Английский (Великобритания)", "en-GB"),
        VoiceMakerLanguage("Немецкий", "de-DE"),
        VoiceMakerLanguage("Французский", "fr-FR"),
        VoiceMakerLanguage("Испанский", "es-ES"),
        VoiceMakerLanguage("Итальянский", "it-IT"),
        VoiceMakerLanguage("Турецкий", "tr-TR"),
        VoiceMakerLanguage("Японский", "ja-JP"),
        VoiceMakerLanguage("Китайский", "zh-CN"),
        VoiceMakerLanguage("Мультиязычные Pro", "multi-lang"),
    ]
    ACCENT_OPTIONS: list[VoiceMakerLanguage] = [
        VoiceMakerLanguage("Без акцента", ""),
        *LANGUAGES,
    ]

    def get_languages(self) -> list[VoiceMakerLanguage]:
        return self.LANGUAGES[:]

    def get_accents(self) -> list[VoiceMakerLanguage]:
        return self.ACCENT_OPTIONS[:]

    def list_voices(self, api_key: str, language_code: str) -> list[VoiceMakerVoice]:
        payload = {"language": language_code} if language_code else {}
        response = self._request_json(self.VOICE_LIST_URL, api_key, payload)

        if not response.get("success"):
            raise RuntimeError(response.get("message", "VoiceMaker не вернул список голосов"))

        data = response.get("data") or {}
        raw_voices = data.get("voices_list") or []
        voices: list[VoiceMakerVoice] = []
        for item in raw_voices:
            voice_id = str(item.get("VoiceId") or item.get("voice_id") or "").strip()
            if not voice_id:
                continue

            label = str(
                item.get("VoiceWebname")
                or item.get("VoiceName")
                or item.get("DisplayName")
                or voice_id
            ).strip()
            language = str(
                item.get("LanguageCode")
                or item.get("Language")
                or language_code
                or ""
            ).strip()
            language_name = str(item.get("LanguageName") or "").strip()
            engine = str(item.get("Engine") or "").strip()
            voices.append(
                VoiceMakerVoice(
                    label=label,
                    voice_id=voice_id,
                    language_code=language,
                    language_name=language_name,
                    engine=engine,
                )
            )

        voices.sort(key=lambda voice: voice.label.lower())
        return voices

    def generate_mp3(
        self,
        api_key: str,
        text: str,
        voice_id: str,
        language_code: str,
        master_volume: int = 14,
        master_speed: int = 0,
        accent_code: str = "",
    ) -> bytes:
        clean_text = text.strip()
        if not api_key:
            raise RuntimeError("Не указан API ключ генератора")
        if not clean_text:
            raise RuntimeError("Введите текст для генерации")
        if not voice_id:
            raise RuntimeError("Не выбран голос генератора")
        if not language_code:
            raise RuntimeError("Не выбран язык генератора")

        payload = {
            "Engine": "neural",
            "VoiceId": voice_id,
            "Text": clean_text,
            "LanguageCode": language_code,
            "OutputFormat": "mp3",
            "SampleRate": "48000",
            "ResponseType": "stream",
            "Effect": "default",
            "MasterVolume": str(max(-20, min(master_volume, 20))),
            "MasterSpeed": str(max(-100, min(master_speed, 100))),
            "MasterPitch": "0",
        }
        clean_accent = accent_code.strip()
        if clean_accent:
            payload["AccentCode"] = clean_accent

        request = urllib.request.Request(
            self.CONVERT_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=120, context=self._ssl_context()) as response:
                content_type = response.headers.get("Content-Type", "")
                body = response.read()
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(details or f"HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ошибка подключения к VoiceMaker: {exc.reason}") from exc

        normalized_content_type = content_type.lower()
        if "audio" in normalized_content_type or "octet-stream" in normalized_content_type:
            return body

        try:
            decoded_body = body.decode("utf-8")
        except UnicodeDecodeError:
            return body

        try:
            parsed = json.loads(decoded_body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("VoiceMaker вернул неожиданный ответ") from exc

        if not parsed.get("success"):
            raise RuntimeError(parsed.get("message", "VoiceMaker не смог сгенерировать аудио"))

        audio_url = parsed.get("path")
        if not audio_url:
            raise RuntimeError("VoiceMaker не вернул аудиопоток или ссылку на файл")

        try:
            with urllib.request.urlopen(audio_url, timeout=120, context=self._ssl_context()) as response:
                return response.read()
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Не удалось скачать сгенерированный файл: {exc.reason}") from exc

    def _request_json(self, url: str, api_key: str, payload: dict) -> dict:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60, context=self._ssl_context()) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(details or f"HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Ошибка подключения к VoiceMaker: {exc.reason}") from exc

        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError("VoiceMaker вернул некорректный JSON") from exc

    def _ssl_context(self) -> ssl.SSLContext:
        if certifi is not None:
            return ssl.create_default_context(cafile=certifi.where())
        return ssl.create_default_context()
