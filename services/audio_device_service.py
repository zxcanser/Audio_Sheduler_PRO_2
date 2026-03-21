from typing import List, Optional
import sounddevice as sd


class AudioDeviceService:
    def get_output_device_names(self) -> List[str]:
        devices = sd.query_devices()
        return [d["name"] for d in devices if d["max_output_channels"] > 0]

    def get_device_id_by_name(self, device_name: str) -> Optional[int]:
        devices = sd.query_devices()
        for idx, device in enumerate(devices):
            if device["name"] == device_name and device["max_output_channels"] > 0:
                return idx
        return None