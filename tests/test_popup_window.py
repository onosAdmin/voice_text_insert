import pytest
from src.popup_window import PopupWindow


def test_popup_creation():
    window = PopupWindow()
    assert window is not None
    assert window.get_position() == (800, 0)
