"""Unit tests for transcribe_audio_segments function."""
import pytest
from unittest.mock import patch, MagicMock
from helper import transcribe_audio_segments


class TestTranscribeAudioSegments:
    """Tests for transcribe_audio_segments function."""

    @patch('helper.sr.Recognizer')
    @patch('helper.sr.AudioFile')
    def test_successful_transcription_single_file(self, mock_audio_file, mock_recognizer_class):
        """Should transcribe single file successfully."""
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.recognize_azure.return_value = "Transcribed text"
        mock_audio_file.return_value.__enter__ = MagicMock()
        mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)
        
        result = transcribe_audio_segments(["file1.wav"], "api_key", "location")
        
        assert result == ["Transcribed text"]

    @patch('helper.sr.Recognizer')
    @patch('helper.sr.AudioFile')
    def test_successful_transcription_multiple_files(self, mock_audio_file, mock_recognizer_class):
        """Should transcribe multiple files and return all results."""
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.recognize_azure.side_effect = ["First text", "Second text"]
        mock_audio_file.return_value.__enter__ = MagicMock()
        mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)
        
        result = transcribe_audio_segments(["file1.wav", "file2.wav"], "api_key", "location")
        
        assert result == ["First text", "Second text"]

    @patch('helper.sr.Recognizer')
    @patch('helper.sr.AudioFile')
    def test_raises_if_all_segments_fail(self, mock_audio_file, mock_recognizer_class):
        """Should raise RuntimeError when all segments fail."""
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.recognize_azure.side_effect = Exception("API Error")
        mock_audio_file.return_value.__enter__ = MagicMock()
        mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)
        
        with pytest.raises(RuntimeError):
            transcribe_audio_segments(["file1.wav"], "api_key", "location")

    @patch('helper.sr.Recognizer')
    @patch('helper.sr.AudioFile')
    @patch('helper.logging')
    def test_partial_success_returns_partial_results(self, mock_logging, mock_audio_file, mock_recognizer_class):
        """Should return partial results when some segments fail."""
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        # First call fails, second succeeds
        mock_recognizer.recognize_azure.side_effect = [Exception("Error"), "Second text"]
        mock_audio_file.return_value.__enter__ = MagicMock()
        mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)
        
        result = transcribe_audio_segments(["file1.wav", "file2.wav"], "api_key", "location")
        
        assert result == ["Second text"]
        mock_logging.warning.assert_called()

    @patch('helper.sr.Recognizer')
    @patch('helper.sr.AudioFile')
    def test_passes_api_key_to_recognizer(self, mock_audio_file, mock_recognizer_class):
        """Should pass API key to recognize_azure."""
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.recognize_azure.return_value = "Text"
        mock_audio_file.return_value.__enter__ = MagicMock()
        mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)
        
        transcribe_audio_segments(["file1.wav"], "test_key_123", "location")
        
        call_kwargs = mock_recognizer.recognize_azure.call_args[1]
        assert call_kwargs['key'] == "test_key_123"

    @patch('helper.sr.Recognizer')
    @patch('helper.sr.AudioFile')
    def test_passes_location_to_recognizer(self, mock_audio_file, mock_recognizer_class):
        """Should pass location to recognize_azure."""
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.recognize_azure.return_value = "Text"
        mock_audio_file.return_value.__enter__ = MagicMock()
        mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)
        
        transcribe_audio_segments(["file1.wav"], "api_key", "westus")
        
        call_kwargs = mock_recognizer.recognize_azure.call_args[1]
        assert call_kwargs['location'] == "westus"

    def test_empty_file_list_returns_empty_list(self):
        """Should return empty list when given empty file list."""
        result = transcribe_audio_segments([], "api_key", "location")
        
        assert result == []

    @patch('helper.sr.Recognizer')
    @patch('helper.sr.AudioFile')
    def test_adjust_for_ambient_noise_called(self, mock_audio_file, mock_recognizer_class):
        """Should call adjust_for_ambient_noise for each file."""
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.recognize_azure.return_value = "Text"
        mock_source = MagicMock()
        mock_audio_file.return_value.__enter__.return_value = mock_source
        mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)
        
        transcribe_audio_segments(["file1.wav"], "api_key", "location")
        
        mock_recognizer.adjust_for_ambient_noise.assert_called_with(mock_source)
