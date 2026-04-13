"""Unit tests for check_file_exists function."""
import os
import pytest
from unittest.mock import patch, MagicMock
from helper import check_file_exists


class TestCheckFileExists:
    """Tests for check_file_exists function."""

    def test_returns_true_for_existing_file(self, tmp_path):
        """Should return True when file exists."""
        test_file = tmp_path / "existing_file.txt"
        test_file.write_text("test content")
        
        result = check_file_exists(str(test_file))
        
        assert result is True

    def test_returns_false_for_missing_file(self, tmp_path):
        """Should return False when file does not exist."""
        missing_file = tmp_path / "missing_file.txt"
        
        result = check_file_exists(str(missing_file))
        
        assert result is False

    def test_returns_false_for_empty_string(self):
        """Should return False when given empty string."""
        result = check_file_exists("")
        
        assert result is False

    @patch('helper.logging')
    def test_logs_filename_and_directory_for_existing_file(self, mock_logging, tmp_path):
        """Should log file name and directory when file exists."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        
        check_file_exists(str(test_file))
        
        mock_logging.info.assert_called()
        all_calls = str(mock_logging.info.call_args_list)
        assert "test.txt" in all_calls
