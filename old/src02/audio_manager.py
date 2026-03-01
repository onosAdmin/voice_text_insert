from typing import List, Dict
import pulsectl


class AudioManager:
    def __init__(self, config=None):
        self.config = config
        self._current_device = None

    def list_devices(self) -> List[Dict[str, str]]:
        devices = []
        try:
            with pulsectl.Pulse("audio-manager") as pulse:
                for source in pulse.source_list():
                    devices.append(
                        {
                            "name": source.name,
                            "description": source.description or source.name,
                            "index": source.index,
                        }
                    )
        except Exception as e:
            print(f"Error listing devices: {e}")
            devices.append({"name": "default", "description": "Default", "index": 0})
        return devices

    def set_device(self, device_name: str):
        self._current_device = device_name

    def get_device(self) -> str:
        return self._current_device or "default"
