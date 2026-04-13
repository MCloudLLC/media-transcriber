"""Unit tests for write_file function."""
import os
import pytest
from unittest.mock import patch, mock_open, MagicMock
from helper import write_file


class TestWriteFile:
    """Tests for write_file function."""

    @patch('helper.get_transcription_file')
    def test_writes_transcribed_text_to_file(self, mock_get_path, tmp_path):
        """Should write joined transcription text to file."""
        output_path = tmp_path / "output.txt"
        mock_get_path.return_value = str(output_path)
        
        transcribed_text = ["First line", "Second line", "Third line"]
        write_file("input.mp4", transcribed_text)
        
        content = output_path.read_text(encoding="utf-8")
        assert content == "First line Second line Third line"

    @patch('helper.get_transcription_file')
    @patch('builtins.open', side_effect=IOError("Write error"))
    def test_raises_on_write_error(self, mock_open_func, mock_get_path):
        """Should re-raise exception after logging error."""
        mock_get_path.return_value = "/path/to/output.txt"
        
        with pytest.raises(IOError):
            write_file("input.mp4", ["text"])

    @patch('helper.get_transcription_file')
    def test_creates_file_at_correct_path(self, mock_get_path, tmp_path):
        """Should create file at path returned by get_transcription_file."""
        expected_path = tmp_path / "custom_output.txt"
        mock_get_path.return_value = str(expected_path)
        
        write_file("input.mp4", ["text"])
        
        assert expected_path.exists()

    @patch('helper.get_transcription_file')
    def test_handles_empty_transcription_list(self, mock_get_path, tmp_path):
        """Should create empty file for empty transcription list."""
        output_path = tmp_path / "empty.txt"
        mock_get_path.return_value = str(output_path)
        
        write_file("input.mp4", [])
        
        content = output_path.read_text(encoding="utf-8")
        assert content == ""

    @patch('helper.get_transcription_file')
    def test_uses_utf8_encoding(self, mock_get_path):
        """Should open file with UTF-8 encoding."""
        mock_get_path.return_value = "/path/to/output.txt"
        
        with patch('builtins.open', mock_open()) as mocked_open:
            write_file("input.mp4", ["text"])
            
            mocked_open.assert_called_once()
            call_kwargs = mocked_open.call_args[1]
            assert call_kwargs.get('encoding') == 'utf-8'
