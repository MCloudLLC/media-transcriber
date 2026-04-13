"""Shared pytest fixtures and configuration."""
import os
import wave
import pytest
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture
def tmp_wav_file(tmp_path):
    """Create a real tiny WAV file (1 second of silence, 16kHz mono 16-bit)."""
    wav_path = tmp_path / "test_audio.wav"
    
    with wave.open(str(wav_path), 'wb') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(16000)  # 16kHz
        # 1 second of silence
        wav_file.writeframes(b'\x00\x00' * 16000)
    
    return wav_path


@pytest.fixture
def mock_audio_segment():
    """MagicMock that behaves like an AudioSegment."""
    audio_mock = MagicMock()
    # AudioSegment length in milliseconds (30 seconds)
    audio_mock.__len__.return_value = 30000
    
    # Support slicing
    def getitem(key):
        sliced = MagicMock()
        sliced.__len__.return_value = 1000  # 1 second slice
        sliced.export = MagicMock()
        return sliced
    
    audio_mock.__getitem__ = getitem
    audio_mock.export = MagicMock()
    
    return audio_mock


@pytest.fixture
def azure_env_vars(monkeypatch):
    """Set Azure environment variables for test duration."""
    monkeypatch.setenv("AZURE_SPEECH_KEY", "test_api_key_12345")
    monkeypatch.setenv("AZURE_AI_LOCATION", "eastus")
    return {
        "key": "test_api_key_12345",
        "location": "eastus"
    }
