"""Unit tests for get_transcription_file function."""
import os
import pytest
from helper import get_transcription_file


class TestGetTranscriptionFile:
    """Tests for get_transcription_file function."""

    def test_returns_txt_path_same_directory(self):
        """Should return .txt path in same directory as input."""
        input_file = "/path/to/video.mp4"
        
        result = get_transcription_file(input_file)
        
        assert result.endswith("video_transcription.txt")
        assert "/path/to/" in result or "\\path\\to\\" in result

    def test_handles_path_with_spaces(self):
        """Should handle file paths with spaces."""
        input_file = "/path/to/my video file.mp4"
        
        result = get_transcription_file(input_file)
        
        assert "my video file_transcription.txt" in result

    def test_handles_no_extension(self):
        """Should handle file with no extension."""
        input_file = "/path/to/videofile"
        
        result = get_transcription_file(input_file)
        
        assert result.endswith("videofile_transcription.txt")

    def test_handles_multiple_dots_in_name(self):
        """Should preserve dots in filename."""
        input_file = "/path/to/video.backup.mp4"
        
        result = get_transcription_file(input_file)
        
        assert "video.backup_transcription.txt" in result

    def test_returns_absolute_path(self):
        """Should return absolute path."""
        input_file = "relative/path/video.mp4"
        
        result = get_transcription_file(input_file)
        
        assert os.path.isabs(result)
