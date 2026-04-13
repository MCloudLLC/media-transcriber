"""Unit tests for load_audio_segments function."""
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
from helper import load_audio_segments


class TestLoadAudioSegments:
    """Tests for load_audio_segments function."""

    @patch('helper.tempfile.mkdtemp')
    def test_short_audio_returns_single_segment(self, mock_mkdtemp, mock_audio_segment, tmp_path):
        """Should return single segment for audio <= 1 minute."""
        mock_mkdtemp.return_value = str(tmp_path)
        # Audio is 30 seconds (30000 ms) - less than 1 minute
        mock_audio_segment.__len__.return_value = 30000

        result = load_audio_segments(mock_audio_segment)

        assert len(result) == 1

    @patch('helper.tempfile.mkdtemp')
    def test_long_audio_splits_into_segments(self, mock_mkdtemp, tmp_path):
        """Should split audio > 1 minute into multiple segments."""
        mock_mkdtemp.return_value = str(tmp_path)
        # Audio is 3 minutes (180000 ms)
        mock_audio = MagicMock()
        mock_audio.__len__.return_value = 180000

        def getitem(obj, key):
            sliced = MagicMock()
            sliced.export = MagicMock()
            return sliced
        mock_audio.__getitem__ = getitem

        result = load_audio_segments(mock_audio)

        assert len(result) == 3

    @patch('helper.tempfile.mkdtemp')
    def test_exact_one_minute_audio(self, mock_mkdtemp, tmp_path):
        """Should handle exactly 60000ms (1 minute) audio."""
        mock_mkdtemp.return_value = str(tmp_path)
        # Exactly 1 minute
        mock_audio = MagicMock()
        mock_audio.__len__.return_value = 60000

        def getitem(obj, key):
            sliced = MagicMock()
            sliced.export = MagicMock()
            return sliced
        mock_audio.__getitem__ = getitem

        result = load_audio_segments(mock_audio)

        assert len(result) == 1

    @patch('helper.tempfile.mkdtemp')
    def test_files_written_to_temp_dir(self, mock_mkdtemp, mock_audio_segment, tmp_path):
        """Should write files to temp directory, not CWD."""
        temp_dir = str(tmp_path / "temp_audio")
        os.makedirs(temp_dir, exist_ok=True)
        mock_mkdtemp.return_value = temp_dir

        result = load_audio_segments(mock_audio_segment)

        mock_mkdtemp.assert_called_once()
        for path in result:
            assert path.startswith(temp_dir)

    @patch('helper.tempfile.mkdtemp')
    def test_returns_list_of_paths(self, mock_mkdtemp, mock_audio_segment, tmp_path):
        """Should return list of file path strings."""
        mock_mkdtemp.return_value = str(tmp_path)

        result = load_audio_segments(mock_audio_segment)

        assert isinstance(result, list)
        assert all(isinstance(path, str) for path in result)

    @patch('helper.tempfile.mkdtemp')
    def test_segment_names_are_unique(self, mock_mkdtemp, tmp_path):
        """Should generate unique filenames for each segment."""
        mock_mkdtemp.return_value = str(tmp_path)
        # 2 minutes of audio
        mock_audio = MagicMock()
        mock_audio.__len__.return_value = 120000

        def getitem(obj, key):
            sliced = MagicMock()
            sliced.export = MagicMock()
            return sliced
        mock_audio.__getitem__ = getitem

        result = load_audio_segments(mock_audio)

        assert len(result) == len(set(result))
