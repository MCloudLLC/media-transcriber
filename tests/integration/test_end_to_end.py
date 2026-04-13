"""Integration tests for end-to-end transcription workflow.

Integration tests require AZURE_SPEECH_KEY and AZURE_AI_LOCATION environment variables.
Run with: pytest tests/integration/test_end_to_end.py
Skip with: pytest -m "not integration"
"""
import os
import pytest
from pathlib import Path

# Skip all tests in this module if Azure credentials are not set
pytestmark = pytest.mark.integration

skip_no_credentials = pytest.mark.skipif(
    not os.environ.get('AZURE_SPEECH_KEY') or not os.environ.get('AZURE_AI_LOCATION'),
    reason="AZURE_SPEECH_KEY and AZURE_AI_LOCATION environment variables required for integration tests"
)


class TestEndToEnd:
    """End-to-end integration tests with real Azure API."""

    @skip_no_credentials
    def test_transcribes_real_wav_file(self, tmp_wav_file):
        """
        Should transcribe a real WAV file using Azure Speech API.
        
        This test requires:
        - AZURE_SPEECH_KEY environment variable
        - AZURE_AI_LOCATION environment variable
        - A real WAV file (provided by tmp_wav_file fixture)
        
        Note: This test will make real API calls to Azure and may incur costs.
        """
        from helper import (
            load_audio_segments,
            transcribe_audio_segments,
            clean_up_temp_files
        )
        
        api_key = os.environ.get('AZURE_SPEECH_KEY')
        api_location = os.environ.get('AZURE_AI_LOCATION')
        
        # Load audio segments
        audio_files = load_audio_segments(str(tmp_wav_file))
        
        try:
            # Transcribe (may return empty for silence, but shouldn't raise)
            result = transcribe_audio_segments(audio_files, api_key, api_location)
            
            # Verify result structure
            assert isinstance(result, list)
            # For silence, Azure may return empty or error, so we just verify it doesn't crash
            
        finally:
            # Clean up temp files
            clean_up_temp_files(audio_files)

    @skip_no_credentials
    def test_handles_missing_audio_file(self):
        """Should handle missing audio file gracefully."""
        from helper import check_file_exists
        
        result = check_file_exists("nonexistent_file.wav")
        
        assert result is False

    @skip_no_credentials
    def test_write_and_read_transcription_file(self, tmp_path):
        """Should write transcription to file and verify content."""
        from helper import write_file, get_transcription_file
        
        test_video = tmp_path / "test_video.mp4"
        test_video.touch()
        
        transcribed_text = ["Hello world", "This is a test"]
        
        # Write transcription
        write_file(str(test_video), transcribed_text)
        
        # Get expected output path
        output_file = get_transcription_file(str(test_video))
        
        # Verify file was created and content is correct
        assert os.path.exists(output_file)
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert content == "Hello world This is a test"
