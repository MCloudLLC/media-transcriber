"""Unit tests for helper.is_youtube_url() and helper.download_youtube_audio()."""
import os
import pytest
from unittest.mock import MagicMock, patch

import helper


class TestIsYoutubeUrl:
    """Tests for the is_youtube_url function."""

    def test_recognizes_youtube_watch_url(self):
        """Should return True for standard youtube.com/watch URL."""
        assert helper.is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_recognizes_youtu_be_short_url(self):
        """Should return True for youtu.be short URL."""
        assert helper.is_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_recognizes_youtube_without_www(self):
        """Should return True for youtube.com without www prefix."""
        assert helper.is_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_returns_false_for_local_file(self):
        """Should return False for local file paths."""
        assert helper.is_youtube_url("video.mp4") is False
        assert helper.is_youtube_url("/path/to/video.mp4") is False

    def test_returns_false_for_other_url(self):
        """Should return False for non-YouTube URLs."""
        assert helper.is_youtube_url("https://vimeo.com/video/123") is False
        assert helper.is_youtube_url("https://example.com/video.mp4") is False

    def test_returns_false_for_empty_string(self):
        """Should return False for empty input."""
        assert helper.is_youtube_url("") is False


class TestDownloadYoutubeAudio:
    """Tests for the download_youtube_audio function."""

    def test_raises_import_error_if_yt_dlp_missing(self):
        """Should raise ImportError with helpful message if yt-dlp is not installed."""
        with patch.dict("sys.modules", {"yt_dlp": None}):
            with pytest.raises(ImportError, match="yt-dlp"):
                helper.download_youtube_audio("https://youtube.com/watch?v=test")

    def test_returns_downloaded_file_path(self, tmp_path):
        """Should return path to the downloaded WAV file."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"title": "Test Video"}
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        # Pre-create the expected output file to simulate yt-dlp's download
        fake_wav = tmp_path / "Test Video.wav"
        fake_wav.write_bytes(b"fake audio data")

        with patch.dict("sys.modules", {"yt_dlp": mock_yt_dlp}), \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            result = helper.download_youtube_audio("https://youtube.com/watch?v=test")

        assert result == str(fake_wav)

    def test_falls_back_to_any_wav_if_title_mismatch(self, tmp_path):
        """Should find WAV file even if yt-dlp sanitizes the title."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"title": "My Video (official)"}
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        # Simulate yt-dlp sanitizing the filename
        sanitized_wav = tmp_path / "My Video _official_.wav"
        sanitized_wav.write_bytes(b"fake audio data")

        with patch.dict("sys.modules", {"yt_dlp": mock_yt_dlp}), \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            result = helper.download_youtube_audio("https://youtube.com/watch?v=test")

        assert result.endswith(".wav")
        assert os.path.dirname(result) == str(tmp_path)

    def test_raises_file_not_found_if_no_wav_produced(self, tmp_path):
        """Should raise FileNotFoundError if no WAV file is found after download."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"title": "Some Video"}
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        # Do NOT create any WAV file — simulate a failed postprocessing step
        with patch.dict("sys.modules", {"yt_dlp": mock_yt_dlp}), \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            with pytest.raises(FileNotFoundError):
                helper.download_youtube_audio("https://youtube.com/watch?v=test")

    def test_propagates_download_error(self, tmp_path):
        """Should re-raise exceptions from yt-dlp (e.g. network errors)."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = Exception("Network error")
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        mock_yt_dlp = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value = mock_ydl

        with patch.dict("sys.modules", {"yt_dlp": mock_yt_dlp}), \
             patch("tempfile.mkdtemp", return_value=str(tmp_path)):
            with pytest.raises(Exception, match="Network error"):
                helper.download_youtube_audio("https://youtube.com/watch?v=test")
