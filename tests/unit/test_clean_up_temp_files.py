"""Unit tests for clean_up_temp_files function."""
import os
import pytest
from pathlib import Path
from helper import clean_up_temp_files


class TestCleanUpTempFiles:
    """Tests for clean_up_temp_files function."""

    def test_deletes_existing_files(self, tmp_path):
        """Should delete all existing files in the list."""
        file1 = tmp_path / "temp1.wav"
        file2 = tmp_path / "temp2.wav"
        file1.write_text("test")
        file2.write_text("test")
        
        files = [str(file1), str(file2)]
        clean_up_temp_files(files)
        
        assert not file1.exists()
        assert not file2.exists()

    def test_ignores_missing_files(self, tmp_path):
        """Should not raise exception when files don't exist."""
        missing_file = tmp_path / "nonexistent.wav"
        
        files = [str(missing_file)]
        clean_up_temp_files(files)  # Should not raise

    def test_empty_list(self):
        """Should handle empty list without error."""
        clean_up_temp_files([])  # Should not raise

    def test_partial_delete(self, tmp_path):
        """Should delete existing files and ignore missing ones."""
        existing = tmp_path / "exists.wav"
        existing.write_text("test")
        missing = tmp_path / "missing.wav"
        
        files = [str(existing), str(missing)]
        clean_up_temp_files(files)
        
        assert not existing.exists()
