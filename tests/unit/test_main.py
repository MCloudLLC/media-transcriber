"""Unit tests for main.py."""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

import main


class TestMain:
    """Tests for main.py execution flow."""

    def test_exits_if_no_args(self, monkeypatch):
        """Should exit when no arguments provided."""
        monkeypatch.setattr(sys, "argv", ["main.py"])
        with pytest.raises(SystemExit) as exc:
            main.main()
        assert exc.value.code != 0

    def test_exits_if_file_not_found(self, monkeypatch):
        """Should exit with code 1 when file doesn't exist."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "nonexistent.mp4"])
        with patch("helper.check_file_exists", return_value=False):
            with pytest.raises(SystemExit) as exc:
                main.main()
        assert exc.value.code == 1

    def test_exits_if_audio_extraction_fails(self, monkeypatch):
        """Should exit with code 1 when audio extraction fails."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "test.mp4"])
        with patch("helper.check_file_exists", return_value=True), \
             patch("helper.get_audio_channel", return_value=None), \
             patch("helper.clean_up_temp_files"):
            with pytest.raises(SystemExit) as exc:
                main.main()
        assert exc.value.code == 1

    def test_cleanup_called_in_finally_on_exception(self, monkeypatch):
        """Should call clean_up_temp_files in finally when transcription raises."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "test.mp4", "--backend", "azure"])
        mock_cleanup = MagicMock()
        with patch("helper.check_file_exists", return_value=True), \
             patch("helper.get_audio_channel", return_value=MagicMock()), \
             patch("helper.load_audio_segments", return_value=["seg1.wav"]), \
             patch("helper.transcribe_audio_segments", side_effect=RuntimeError("API Error")), \
             patch("helper.clean_up_temp_files", mock_cleanup):
            with pytest.raises(SystemExit):
                main.main()
        mock_cleanup.assert_called_once_with(["seg1.wav"])

    def test_cleanup_called_on_success(self, monkeypatch):
        """Should call clean_up_temp_files on successful run."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "test.mp4", "--backend", "azure"])
        monkeypatch.setattr(sys, "platform", "win32")
        mock_cleanup = MagicMock()
        with patch("helper.check_file_exists", return_value=True), \
             patch("helper.get_audio_channel", return_value=MagicMock()), \
             patch("helper.load_audio_segments", return_value=["seg1.wav"]), \
             patch("helper.transcribe_audio_segments", return_value=["text"]), \
             patch("helper.write_file"), \
             patch("helper.get_transcription_file", return_value="output.txt"), \
             patch("helper.clean_up_temp_files", mock_cleanup), \
             patch("main.os.startfile"):
            main.main()
        mock_cleanup.assert_called_once_with(["seg1.wav"])

    def test_exits_if_missing_azure_speech_key(self, monkeypatch):
        """Should exit with code 1 when AZURE_SPEECH_KEY not set."""
        monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "test.mp4"])
        with pytest.raises(SystemExit) as exc:
            main.main()
        assert exc.value.code == 1

    def test_exits_if_missing_azure_location(self, monkeypatch):
        """Should exit with code 1 when AZURE_AI_LOCATION not set."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.delenv("AZURE_AI_LOCATION", raising=False)
        monkeypatch.setattr(sys, "argv", ["main.py", "test.mp4"])
        with pytest.raises(SystemExit) as exc:
            main.main()
        assert exc.value.code == 1

    def test_opens_file_on_windows(self, monkeypatch):
        """Should use os.startfile on Windows."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "test.mp4", "--backend", "azure"])
        monkeypatch.setattr(sys, "platform", "win32")
        with patch("helper.check_file_exists", return_value=True), \
             patch("helper.get_audio_channel", return_value=MagicMock()), \
             patch("helper.load_audio_segments", return_value=["seg1.wav"]), \
             patch("helper.transcribe_audio_segments", return_value=["text"]), \
             patch("helper.write_file"), \
             patch("helper.get_transcription_file", return_value="output.txt"), \
             patch("helper.clean_up_temp_files"), \
             patch("main.os.startfile") as mock_startfile:
            main.main()
        mock_startfile.assert_called_once_with("output.txt")

    def test_opens_file_on_macos(self, monkeypatch):
        """Should use subprocess.run with 'open' on macOS."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "test.mp4", "--backend", "azure"])
        monkeypatch.setattr(sys, "platform", "darwin")
        with patch("helper.check_file_exists", return_value=True), \
             patch("helper.get_audio_channel", return_value=MagicMock()), \
             patch("helper.load_audio_segments", return_value=["seg1.wav"]), \
             patch("helper.transcribe_audio_segments", return_value=["text"]), \
             patch("helper.write_file"), \
             patch("helper.get_transcription_file", return_value="output.txt"), \
             patch("helper.clean_up_temp_files"), \
             patch("main.subprocess.run") as mock_run:
            main.main()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][0] == "open"

    def test_opens_file_on_linux(self, monkeypatch):
        """Should use subprocess.run with 'xdg-open' on Linux."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "test.mp4", "--backend", "azure"])
        monkeypatch.setattr(sys, "platform", "linux")
        with patch("helper.check_file_exists", return_value=True), \
             patch("helper.get_audio_channel", return_value=MagicMock()), \
             patch("helper.load_audio_segments", return_value=["seg1.wav"]), \
             patch("helper.transcribe_audio_segments", return_value=["text"]), \
             patch("helper.write_file"), \
             patch("helper.get_transcription_file", return_value="output.txt"), \
             patch("helper.clean_up_temp_files"), \
             patch("main.subprocess.run") as mock_run:
            main.main()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0][0] == "xdg-open"

    def test_full_successful_run(self, monkeypatch):
        """Should complete full happy-path flow successfully."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "test.mp4", "--backend", "azure"])
        monkeypatch.setattr(sys, "platform", "win32")
        mock_audio = MagicMock()
        mock_check = MagicMock(return_value=True)
        mock_get_audio = MagicMock(return_value=mock_audio)
        mock_load = MagicMock(return_value=["seg1.wav", "seg2.wav"])
        mock_transcribe = MagicMock(return_value=["First text", "Second text"])
        mock_write = MagicMock()
        mock_cleanup = MagicMock()
        with patch("helper.is_youtube_url", return_value=False), \
             patch("helper.check_file_exists", mock_check), \
             patch("helper.get_audio_channel", mock_get_audio), \
             patch("helper.load_audio_segments", mock_load), \
             patch("helper.transcribe_audio_segments", mock_transcribe), \
             patch("helper.write_file", mock_write), \
             patch("helper.get_transcription_file", return_value="output.txt"), \
             patch("helper.clean_up_temp_files", mock_cleanup), \
             patch("main.os.startfile"):
            main.main()
        mock_check.assert_called_with("test.mp4")
        mock_get_audio.assert_called_with("test.mp4")
        mock_load.assert_called_with(mock_audio)
        mock_transcribe.assert_called_with(["seg1.wav", "seg2.wav"], api_key="key", api_location="loc")
        mock_write.assert_called_with("test.mp4", ["First text", "Second text"], output_dir=None)
        mock_cleanup.assert_called_with(["seg1.wav", "seg2.wav"])

    def test_youtube_url_downloads_audio(self, monkeypatch):
        """Should call download_youtube_audio when input is a YouTube URL."""
        monkeypatch.setenv("AZURE_SPEECH_KEY", "key")
        monkeypatch.setenv("AZURE_AI_LOCATION", "loc")
        monkeypatch.setattr(sys, "argv", ["main.py", "https://youtube.com/watch?v=test", "--backend", "azure"])
        monkeypatch.setattr(sys, "platform", "win32")
        mock_download = MagicMock(return_value="/tmp/yt/video.wav")
        with patch("helper.is_youtube_url", return_value=True), \
             patch("helper.download_youtube_audio", mock_download), \
             patch("helper.get_audio_channel", return_value=MagicMock()), \
             patch("helper.load_audio_segments", return_value=["seg1.wav"]), \
             patch("helper.transcribe_audio_segments", return_value=["text"]), \
             patch("helper.write_file"), \
             patch("helper.get_transcription_file", return_value="output.txt"), \
             patch("helper.clean_up_temp_files"), \
             patch("main.os.startfile"), \
             patch("main.os.path.exists", return_value=False):
            main.main()
        mock_download.assert_called_once_with("https://youtube.com/watch?v=test")
