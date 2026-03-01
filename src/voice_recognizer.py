import json
from typing import Optional, Callable
from vosk import Model, KaldiRecognizer
import pyaudio


class VoiceRecognizer:
    DEFAULT_KEYWORDS = {
        "computer scrivi": "scrivi",
        "computer inserisci": "inserisci",
        "pc correggi": "correggi",
        "computer cancella": "cancella",
    }

    def __init__(
        self,
        models_config: dict = None,
        sample_rate: int = 16000,
        keywords: dict = None,
        dictionary: dict = None,
    ):
        self.sample_rate = sample_rate
        self.models = []
        self.recognizers = []
        self.stream = None
        self.audio = None
        self._callback = None
        self.keywords = keywords or self.DEFAULT_KEYWORDS
        self.dictionary = dictionary or {}
        self.models_config = models_config or {
            "it": {
                "path": "model/vosk-model-small-it-0.22",
                "enabled": True,
                "primary": True,
            }
        }

    def load_models(self):
        for lang, config in self.models_config.items():
            if not config.get("enabled", True):
                continue
            model_path = config.get("path", "model")
            model = Model(model_path)
            is_primary = config.get("primary", False)
            self.models.append((model, is_primary))
            print(f"Caricato modello Vosk: {lang} (primary={is_primary})")

    def create_recognizers(self):
        self.recognizers = []
        for model, is_primary in self.models:
            recognizer = KaldiRecognizer(model, self.sample_rate)
            self.recognizers.append((recognizer, is_primary))
        return self.recognizers

    def create_recognizer(self):
        for recognizer, is_primary in self.recognizers:
            if is_primary:
                return recognizer
        if self.recognizers:
            return self.recognizers[0][0]
        return None

    def is_keyword(self, text: str) -> bool:
        text_lower = text.lower().strip()
        return any(text_lower.startswith(kw) for kw in self.keywords.keys())

    def get_command(self, text: str) -> Optional[str]:
        text_lower = text.lower().strip()
        for kw, cmd in self.keywords.items():
            if text_lower.startswith(kw):
                return cmd
        return None

    def apply_dictionary(self, text: str) -> str:
        if not hasattr(self, "dictionary") or not self.dictionary:
            return text
        result = text
        for word, replacement in self.dictionary.items():
            result = result.replace(word, replacement)
        return result

    def start_listening(self, callback: Callable[[str], None], device: str = None):
        self._callback = callback
        self.audio = pyaudio.PyAudio()

        device_index = None
        if device and device != "default":
            for i in range(self.audio.get_device_count()):
                dev_info = self.audio.get_device_info_by_index(i)
                if dev_info["name"] == device:
                    device_index = i
                    break

        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=1024,
        )

        while self.stream.is_active():
            data = self.stream.read(1024, exception_on_overflow=False)
            recognizer = self.create_recognizer()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "")
                if text:
                    self._callback(text)

    def stop_listening(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
