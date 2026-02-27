import pytest
from unittest.mock import MagicMock, patch
from src.audio_manager import AudioManager


@patch("src.audio_manager.pulsectl")
def test_list_devices(mock_pulse):
    mock_source1 = MagicMock()
    mock_source1.name = "Microphone"
    mock_source1.description = "USB Microphone"
    mock_source1.index = 0

    mock_source2 = MagicMock()
    mock_source2.name = "default"
    mock_source2.description = "Default"
    mock_source2.index = 1

    mock_pulse.Pulse.return_value.__enter__.return_value.source_list.return_value = [
        mock_source1,
        mock_source2,
    ]
    manager = AudioManager()
    devices = manager.list_devices()
    assert len(devices) == 2
    assert "Microphone" in devices[0]["name"]
