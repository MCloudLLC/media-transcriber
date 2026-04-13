"""Unit tests for helper.transcribe_with_whisper()."""
import pytest
from unittest.mock import MagicMock, patch

import helper


class TestTranscribeWithWhisper:
    """Tests for the transcribe_with_whisper function."""

    def test_raises_import_error_if_faster_whisper_missing(self):
        """Should raise ImportError with helpful message if faster-whisper is not installed."""
        with patch.dict("sys.modules", {"faster_whisper": None}):
            with pytest.raises(ImportError, match="faster-whisper"):
                helper.transcribe_with_whisper(["audio.wav"])

    def test_transcribes_single_file(self):
        """Should return a list with one text entry for a single audio file."""
        mock_segment = MagicMock()
        mock_segment.text = "  Hello world  "
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], MagicMock())

        mock_fw = MagicMock()
        mock_fw.WhisperModel.return_value = mock_model

        with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
            result = helper.transcribe_with_whisper(["audio.wav"])

        assert result == ["Hello world"]

    def test_transcribes_multiple_files(self):
        """Should return one text entry per audio file."""
        seg1 = MagicMock()
        seg1.text = "First"
        seg2 = MagicMock()
        seg2.text = "Second"
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = [
            ([seg1], MagicMock()),
            ([seg2], MagicMock()),
        ]

        mock_fw = MagicMock()
        mock_fw.WhisperModel.return_value = mock_model

        with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
            result = helper.transcribe_with_whisper(["part1.wav", "part2.wav"])

        assert result == ["First", "Second"]

    def test_uses_default_base_model(self):
        """Should load the 'base' model when no model_size is specified."""
        mock_segment = MagicMock()
        mock_segment.text = "text"
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], MagicMock())

        mock_fw = MagicMock()
        mock_fw.WhisperModel.return_value = mock_model

        with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
            helper.transcribe_with_whisper(["audio.wav"])

        mock_fw.WhisperModel.assert_called_once_with("base", device="cpu", compute_type="int8")

    def test_uses_custom_model_size(self):
        """Should load the specified model size."""
        mock_segment = MagicMock()
        mock_segment.text = "text"
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment], MagicMock())

        mock_fw = MagicMock()
        mock_fw.WhisperModel.return_value = mock_model

        with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
            helper.transcribe_with_whisper(["audio.wav"], model_size="small")

        mock_fw.WhisperModel.assert_called_once_with("small", device="cpu", compute_type="int8")

    def test_joins_multiple_segments_within_file(self):
        """Should join multiple Whisper segments from one file with spaces."""
        seg1 = MagicMock()
        seg1.text = "Hello"
        seg2 = MagicMock()
        seg2.text = "world"
        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([seg1, seg2], MagicMock())

        mock_fw = MagicMock()
        mock_fw.WhisperModel.return_value = mock_model

        with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
            result = helper.transcribe_with_whisper(["audio.wav"])

        assert result == ["Hello world"]

    def test_raises_runtime_error_if_all_files_fail(self):
        """Should raise RuntimeError if every file fails to transcribe."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("model error")

        mock_fw = MagicMock()
        mock_fw.WhisperModel.return_value = mock_model

        with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
            with pytest.raises(RuntimeError):
                helper.transcribe_with_whisper(["bad.wav"])

    def test_partial_success_returns_successful_segments(self):
        """Should return successful results when only some files fail."""
        seg = MagicMock()
        seg.text = "success"
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = [
            ([seg], MagicMock()),
            Exception("model error"),
        ]

        mock_fw = MagicMock()
        mock_fw.WhisperModel.return_value = mock_model

        with patch.dict("sys.modules", {"faster_whisper": mock_fw}):
            result = helper.transcribe_with_whisper(["good.wav", "bad.wav"])

        assert result == ["success"]
