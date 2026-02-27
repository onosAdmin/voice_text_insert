import pytest
from src.settings_window import SettingsWindow


def test_settings_creation():
    window = SettingsWindow(devices=[{"name": "mic1", "description": "Microphone 1"}])
    assert window is not None
