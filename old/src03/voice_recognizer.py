import json
from typing import Optional, Callable
from vosk import Model, KaldiRecognizer
import pyaudio


class VoiceRecognizer:
    KEYWORDS = {
        "computer scrivi": "scrivi",
        "computer inserisci": "inserisci",
        "pc correggi": "correggi",
    }

    def __init__(self, model_path: str = "model", sample_rate: int = 16000):
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model = None
        self.recognizer = None
        self.stream = None
        self.audio = None
        self._callback = None

    def load_model(self):
        self.model = Model(self.model_path)
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)

    def create_recognizer(self):
        return KaldiRecognizer(self.model, self.sample_rate)

    def is_keyword(self, text: str) -> bool:
        text_lower = text.lower().strip()
        return any(text_lower.startswith(kw) for kw in self.KEYWORDS.keys())

    def get_command(self, text: str) -> Optional[str]:
        text_lower = text.lower().strip()
        for kw, cmd in self.KEYWORDS.items():
            if text_lower.startswith(kw):
                return cmd
        return None

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
            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get("text", "")
                if text:
                    self._callback(text)

    def stop_listening(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
