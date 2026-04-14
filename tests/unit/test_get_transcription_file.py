"""Unit tests for get_transcription_file and sanitize_filename functions."""
import os
import pytest
from helper import get_transcription_file, sanitize_filename


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_replaces_whitespace(self):
        assert sanitize_filename("my video file") == "my_video_file"

    def test_removes_special_characters(self):
        assert sanitize_filename('video<>:"/\\|?*name') == "video_name"

    def test_collapses_consecutive_underscores(self):
        assert sanitize_filename("a___b---c") == "a_b_c"

    def test_strips_leading_trailing_dots(self):
        assert sanitize_filename("..hidden..") == "hidden"

    def test_returns_fallback_for_empty_result(self):
        assert sanitize_filename("***") == "transcription"

    def test_preserves_normal_names(self):
        assert sanitize_filename("my-video_2024") == "my-video_2024"

    def test_handles_youtube_titles(self):
        result = sanitize_filename("My Video!! (Official) [4K] | 2024")
        assert " " not in result
        assert "?" not in result
        assert "|" not in result


class TestGetTranscriptionFile:
    """Tests for get_transcription_file function."""

    def test_defaults_to_cwd(self):
        """Should place output in CWD when no output_dir given."""
        result = get_transcription_file("/tmp/video.mp4")
        assert os.path.dirname(result) == os.getcwd()
        assert result.endswith("video_transcription.txt")

    def test_uses_output_dir_when_specified(self, tmp_path):
        """Should place output in specified directory."""
        result = get_transcription_file("/tmp/video.mp4", output_dir=str(tmp_path))
        assert os.path.dirname(result) == str(tmp_path)
        assert result.endswith("video_transcription.txt")

    def test_sanitizes_filename(self):
        """Should sanitize special characters in filename."""
        result = get_transcription_file("/tmp/My Video!! (Official).mp4")
        basename = os.path.basename(result)
        assert " " not in basename
        assert "!" not in basename
        assert basename.endswith("_transcription.txt")

    def test_handles_no_extension(self):
        """Should handle file with no extension."""
        result = get_transcription_file("/path/to/videofile")
        assert result.endswith("videofile_transcription.txt")

    def test_returns_absolute_path(self):
        """Should return absolute path."""
        result = get_transcription_file("relative/path/video.mp4")
        assert os.path.isabs(result)
