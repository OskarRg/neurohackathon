import pytest
import os
from unittest.mock import MagicMock, patch
from source.philosopher.gemini_brain import GeminiBrain


def test_init_raises_error_without_api_key():
    """Check if the key is in .env .env"""
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.getenv", return_value=None):
            with pytest.raises(ValueError, match="Missing key `GEMINI_API_KEY`"):
                GeminiBrain()


@patch("source.philosopher.gemini_brain.genai")
@patch("os.getenv")
def test_init_success(mock_getenv, mock_genai):
    """Check ig the key exists"""
    mock_getenv.return_value = "FAKE_API_KEY_123"

    brain = GeminiBrain()

    mock_genai.configure.assert_called_with(api_key="FAKE_API_KEY_123")
    mock_genai.GenerativeModel.assert_called_once()
    assert brain.model is not None


@patch("source.philosopher.gemini_brain.genai")
@patch("os.getenv")
def test_generate_stoic_advice_clean_output(mock_getenv, mock_genai):
    """Check text formatting"""
    mock_getenv.return_value = "FAKE_KEY"

    mock_response = MagicMock()
    mock_response.text = "Does the *segfault* cause distress? Use `debug` logic."
    mock_model_instance = mock_genai.GenerativeModel.return_value
    mock_model_instance.generate_content.return_value = mock_response
    brain = GeminiBrain()
    result = brain.generate_stoic_advice("Help me")

    expected_text = "Does the segfault cause distress? Use debug logic."
    assert result == expected_text


@patch("source.philosopher.gemini_brain.genai")
@patch("os.getenv")
def test_generate_stoic_advice_api_failure(mock_getenv, mock_genai):
    """Check text fallback"""
    mock_getenv.return_value = "FAKE_KEY"
    mock_model_instance = mock_genai.GenerativeModel.return_value
    mock_model_instance.generate_content.side_effect = Exception(
        "Google Server Error 500"
    )

    brain = GeminiBrain()
    result = brain.generate_stoic_advice("Help me")

    assert "Patience. The API is silent" in result
