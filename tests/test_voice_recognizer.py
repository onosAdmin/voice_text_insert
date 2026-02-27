import pytest
from src.voice_recognizer import VoiceRecognizer


def test_command_detection():
    recognizer = VoiceRecognizer()
    assert recognizer.is_keyword("computer scrivi") == True
    assert recognizer.is_keyword("computer inserisci") == True
    assert recognizer.is_keyword("pc correggi") == True
    assert recognizer.is_keyword("ciao") == False


def test_get_command():
    recognizer = VoiceRecognizer()
    assert recognizer.get_command("computer scrivi") == "scrivi"
    assert recognizer.get_command("computer inserisci") == "inserisci"
    assert recognizer.get_command("pc correggi") == "correggi"
