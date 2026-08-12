import platform
import re
from typing import List, Optional
import sounddevice as sd


class AudioDeviceService:
    DEFAULT_OUTPUT_DEVICE_NAME = "Системное устройство по умолчанию"

    def get_output_device_names(self) -> List[str]:
        devices = self._query_devices()
        output_devices = [
            self._build_device_info(index, device)
            for index, device in enumerate(devices)
            if device["max_output_channels"] > 0
        ]

        if platform.system() != "Windows":
            return self._with_default_output_device([device["name"] for device in output_devices])

        deduplicated_devices: dict[str, dict] = {}
        for device in output_devices:
            dedupe_key = self._normalize_windows_device_name(device["name"])
            existing = deduplicated_devices.get(dedupe_key)
            if existing is None or self._get_windows_device_rank(device) < self._get_windows_device_rank(existing):
                deduplicated_devices[dedupe_key] = device

        return self._with_default_output_device([device["name"] for device in deduplicated_devices.values()])

    def refresh_output_device_names(self) -> List[str]:
        try:
            sd._terminate()
            sd._initialize()
        except Exception:
            pass

        return self.get_output_device_names()

    def get_device_id_by_name(self, device_name: str) -> Optional[int]:
        if not device_name or device_name == self.DEFAULT_OUTPUT_DEVICE_NAME:
            return None

        devices = [
            self._build_device_info(index, device)
            for index, device in enumerate(self._query_devices())
            if device["max_output_channels"] > 0
        ]

        for device in devices:
            if device["name"] == device_name:
                return device["id"]

        if platform.system() != "Windows":
            return None

        normalized_name = self._normalize_windows_device_name(device_name)
        matching_devices = [
            device for device in devices
            if self._normalize_windows_device_name(device["name"]) == normalized_name
        ]
        if matching_devices:
            best_device = min(matching_devices, key=self._get_windows_device_rank)
            return best_device["id"]

        return None

    def _query_devices(self):
        return sd.query_devices()

    def _with_default_output_device(self, device_names: List[str]) -> List[str]:
        unique_names = [name for name in device_names if name and name != self.DEFAULT_OUTPUT_DEVICE_NAME]
        return [self.DEFAULT_OUTPUT_DEVICE_NAME, *unique_names]

    def _build_device_info(self, device_id: int, device) -> dict:
        hostapis = sd.query_hostapis()
        hostapi_index = device["hostapi"]
        hostapi_name = hostapis[hostapi_index]["name"] if 0 <= hostapi_index < len(hostapis) else ""
        return {
            "id": device_id,
            "name": device["name"],
            "hostapi": hostapi_name,
        }

    def _normalize_windows_device_name(self, name: str) -> str:
        normalized = name.lower().strip()
        normalized = re.sub(r"\b(mme|windows directsound|windows wasapi|wdm-ks|asio)\b", "", normalized)
        normalized = re.sub(r"[\[\]\(\),_-]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _get_windows_device_rank(self, device: dict) -> tuple[int, int, str]:
        hostapi = device["hostapi"].lower()
        if "wasapi" in hostapi:
            priority = 0
        elif "directsound" in hostapi:
            priority = 1
        elif "mme" in hostapi:
            priority = 2
        elif "wdm-ks" in hostapi:
            priority = 3
        else:
            priority = 4

        # Shorter names are usually the cleaner representative among duplicates.
        return (priority, len(device["name"]), device["name"].lower())
