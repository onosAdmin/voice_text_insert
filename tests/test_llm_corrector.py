import pytest
from unittest.mock import patch, MagicMock
from src.llm_corrector import LLMCorrector


@patch("requests.post")
def test_correct_text(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Testo corretto"}}]
    }
    mock_post.return_value = mock_response

    corrector = LLMCorrector(api_key="test-key")
    result = corrector.correct_text("testo", model="anthropic/claude-3-haiku")
    assert result == "Testo corretto"
