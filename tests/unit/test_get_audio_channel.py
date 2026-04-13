"""Unit tests for get_audio_channel function."""
import pytest
from unittest.mock import patch, MagicMock, call
from helper import get_audio_channel


class TestGetAudioChannel:
    """Tests for get_audio_channel function."""

    @patch('helper.AudioSegment')
    def test_returns_audio_segment_on_success(self, mock_audio_segment):
        """Should return AudioSegment when successful."""
        mock_audio = MagicMock()
        mock_audio_segment.from_file.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        
        result = get_audio_channel("test.mp4")
        
        assert result == mock_audio

    @patch('helper.AudioSegment')
    def test_returns_none_on_exception(self, mock_audio_segment):
        """Should return None when exception occurs."""
        mock_audio_segment.from_file.side_effect = Exception("Test error")
        
        result = get_audio_channel("test.mp4")
        
        assert result is None

    @patch('helper.AudioSegment')
    def test_extracts_file_format_from_extension(self, mock_audio_segment):
        """Should extract and use correct file format."""
        mock_audio = MagicMock()
        mock_audio_segment.from_file.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        
        get_audio_channel("test.mp4")
        mock_audio_segment.from_file.assert_called_with("test.mp4", format="mp4")

        get_audio_channel("test.mp3")
        mock_audio_segment.from_file.assert_called_with("test.mp3", format="mp3")

        get_audio_channel("test.wav")
        mock_audio_segment.from_file.assert_called_with("test.wav", format="wav")

    @patch('helper.AudioSegment')
    def test_sets_mono_channel(self, mock_audio_segment):
        """Should set channels to 1 (mono)."""
        mock_audio = MagicMock()
        mock_audio_segment.from_file.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        
        get_audio_channel("test.mp4")
        
        mock_audio.set_channels.assert_called_with(1)

    @patch('helper.AudioSegment')
    def test_sets_frame_rate_16000(self, mock_audio_segment):
        """Should set frame rate to 16000."""
        mock_audio = MagicMock()
        mock_audio_segment.from_file.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        
        get_audio_channel("test.mp4")
        
        mock_audio.set_frame_rate.assert_called_with(16000)

    @patch('helper.AudioSegment')
    def test_sets_sample_width_2(self, mock_audio_segment):
        """Should set sample width to 2 (16-bit)."""
        mock_audio = MagicMock()
        mock_audio_segment.from_file.return_value = mock_audio
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.set_sample_width.return_value = mock_audio
        
        get_audio_channel("test.mp4")
        
        mock_audio.set_sample_width.assert_called_with(2)
