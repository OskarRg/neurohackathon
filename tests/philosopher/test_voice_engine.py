import pytest
import os
from unittest.mock import patch

from source.philosopher.voice_engine import VoiceEngine
from source.philosopher.utils import STOIC_VOICE_ID


def test_init_raises_error_without_api_key():
    """Checks a lacking key in `.env` raises ValueError."""
    with patch.dict(os.environ, {}, clear=True):
        with patch("os.getenv", return_value=None):
            with pytest.raises(ValueError, match="Missing key `ELEVENLABS_API_KEY`"):
                VoiceEngine()


@patch("source.philosopher.voice_engine.ElevenLabs")
@patch("source.philosopher.voice_engine.pygame")
@patch("os.getenv")
def test_init_success(mock_getenv, mock_pygame, mock_elevenlabs):
    """Check proper key initialization."""
    mock_getenv.return_value = "FAKE_API_KEY"
    engine = VoiceEngine()

    mock_elevenlabs.assert_called_once_with(api_key="FAKE_API_KEY")
    mock_pygame.mixer.init.assert_called_once()
    assert engine.voice_id == STOIC_VOICE_ID


@patch("source.philosopher.voice_engine.ElevenLabs")
@patch("source.philosopher.voice_engine.pygame")
@patch("os.getenv")
def test_speak_empty_text_does_nothing(mock_getenv, mock_pygame, mock_elevenlabs):
    """Check ignore empty string."""
    mock_getenv.return_value = "KEY"
    engine = VoiceEngine()

    engine.speak("")
    engine.speak(None)

    mock_elevenlabs.return_value.text_to_speech.convert.assert_not_called()
