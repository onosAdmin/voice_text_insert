import yaml
from pathlib import Path


class ConfigManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config = self._load()

    def _load(self) -> dict:
        if not self.config_path.exists():
            return self._default_config()
        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}

    def _default_config(self) -> dict:
        return {
            "audio": {"default_microphone": "default"},
            "llm": {
                "model1": "anthropic/claude-3-haiku",
                "model2": "meta-llama/llama-3.2-3b-instruct",
                "default_model": 1,
                "api_key": "",
            },
            "settings": {
                "timeout_seconds": 40,
                "popup_position": "top-right",
                "language": "it",
                "vosk_model_path": "model",
            },
        }

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value):
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save()

    def _save(self):
        with open(self.config_path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False)

    def get_audio_device(self) -> str:
        return self.get("audio.default_microphone", "default")

    def set_audio_device(self, device: str):
        self.set("audio.default_microphone", device)

    def get_llm_config(self) -> dict:
        return {
            "model1": self.get("llm.model1"),
            "model2": self.get("llm.model2"),
            "default_model": self.get("llm.default_model", 1),
            "api_key": self.get("llm.api_key", ""),
        }

    def get_settings(self) -> dict:
        return {
            "timeout_seconds": self.get("settings.timeout_seconds", 40),
            "popup_position": self.get("settings.popup_position", "top-right"),
            "language": self.get("settings.language", "it"),
            "vosk_model_path": self.get("settings.vosk_model_path", "model"),
        }

    def get_keywords(self) -> dict:
        keywords = self.get("keywords", {})
        if not keywords:
            return {
                "computer scrivi": "scrivi",
                "computer inserisci": "inserisci",
                "pc correggi": "correggi",
                "computer cancella": "cancella",
            }
        return keywords

    def get_dictionary(self) -> dict:
        return self.get("dictionary", {})
