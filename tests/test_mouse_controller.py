import pytest
from unittest.mock import patch


@patch("src.mouse_controller.subprocess.run")
def test_click_and_type(mock_run):
    from src.mouse_controller import MouseController

    controller = MouseController()
    controller.click_and_type("test text")
    calls = mock_run.call_args_list
    assert any("click" in str(c) for c in calls)
    assert any("type" in str(c) for c in calls)
