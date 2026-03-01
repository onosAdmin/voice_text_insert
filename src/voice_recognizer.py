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
        multi_model_mode: str = "best_confidence",
        confidence_threshold: float = 0.7,
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
        self.multi_model_mode = multi_model_mode
        self.confidence_threshold = confidence_threshold

    def load_models(self):
        for lang, config in self.models_config.items():
            if not config.get("enabled", True):
                continue
            model_path = config.get("path", "model")
            try:
                model = Model(model_path)
            except Exception as e:
                print(f"Errore caricando modello {lang} da {model_path}: {e}")
                continue
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
        if self.recognizers:
            for recognizer, is_primary in self.recognizers:
                if is_primary:
                    return recognizer
            return self.recognizers[0][0]
        if self.models:
            return KaldiRecognizer(self.models[0][0], self.sample_rate)
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

    def _get_confidence(self, recognizer) -> float:
        result_json = recognizer.Result()
        result = json.loads(result_json)
        words = result.get("result", [])
        if not words:
            return 0.0
        return sum(w.get("conf", 0.0) for w in words) / len(words)

    def process_audio_multi(self, data: bytes) -> tuple:
        results = []
        for i, (recognizer, is_primary) in enumerate(self.recognizers):
            recognizer.AcceptWaveform(data)
            result_json = recognizer.Result()
            result = json.loads(result_json)
            text = result.get("text", "")
            if text:
                confidence = self._get_confidence(recognizer)
                lang = (
                    list(self.models_config.keys())[i]
                    if i < len(self.models_config)
                    else f"model_{i}"
                )
                print(
                    f'[{lang}] text="{text}" confidence={confidence:.3f} primary={is_primary}'
                )
                results.append((text, confidence, is_primary))

        if not results:
            return "", 0.0, False

        if self.multi_model_mode == "best_confidence":
            return max(results, key=lambda x: x[1])
        else:  # primary_fallback
            primary_result = None
            for text, conf, is_primary in results:
                if is_primary:
                    primary_result = (text, conf, is_primary)
                    if conf >= self.confidence_threshold:
                        return primary_result

            if primary_result and results:
                best = max(results, key=lambda x: x[1])
                if best[1] >= self.confidence_threshold:
                    return best
                return primary_result

            return primary_result or results[0]

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
