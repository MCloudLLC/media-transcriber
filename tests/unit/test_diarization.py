"""Unit tests for diarization helpers and the diarized pipeline path."""
import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Import torch and huggingface_hub up front so they are present in the sys.modules
# snapshot before any patch.dict(sys.modules, ...) block. Otherwise a lazy `import torch`
# inside a patched context would be evicted on exit, forcing a re-import that fails with
# "_has_torch_function already has a docstring".
import torch  # noqa: F401
import huggingface_hub  # noqa: F401

import helper


class TestMergeTurns:
    """Tests for _merge_turns."""

    def test_merges_adjacent_same_speaker_within_gap(self):
        turns = [(0.0, 1.0, "SPEAKER_00"), (1.2, 2.0, "SPEAKER_00")]
        result = helper._merge_turns(turns, max_gap=0.75)
        assert result == [(0.0, 2.0, "SPEAKER_00")]

    def test_does_not_merge_when_gap_too_large(self):
        turns = [(0.0, 1.0, "SPEAKER_00"), (3.0, 4.0, "SPEAKER_00")]
        result = helper._merge_turns(turns, max_gap=0.75)
        assert result == [(0.0, 1.0, "SPEAKER_00"), (3.0, 4.0, "SPEAKER_00")]

    def test_does_not_merge_different_speakers(self):
        turns = [(0.0, 1.0, "SPEAKER_00"), (1.0, 2.0, "SPEAKER_01")]
        result = helper._merge_turns(turns, max_gap=0.75)
        assert result == turns

    def test_empty(self):
        assert helper._merge_turns([]) == []


class TestBestOverlapSpeaker:
    """Tests for _best_overlap_speaker."""

    def test_picks_max_overlap(self):
        turns = [(0.0, 2.0, "SPEAKER_00"), (2.0, 5.0, "SPEAKER_01")]
        # Segment 1.5-4.5 overlaps SPEAKER_00 by 0.5, SPEAKER_01 by 2.5
        assert helper._best_overlap_speaker(1.5, 4.5, turns) == "SPEAKER_01"

    def test_returns_default_when_no_overlap(self):
        turns = [(10.0, 12.0, "SPEAKER_00")]
        assert helper._best_overlap_speaker(0.0, 1.0, turns, default="UNKNOWN") == "UNKNOWN"


class TestAssignSpeakers:
    """Tests for assign_speakers_to_segments."""

    def test_assigns_and_skips_empty(self):
        asr = [
            {"start": 0.0, "end": 1.0, "text": "Hello"},
            {"start": 1.0, "end": 2.0, "text": "   "},
            {"start": 2.0, "end": 3.0, "text": "World"},
        ]
        turns = [(0.0, 1.5, "SPEAKER_00"), (1.5, 3.0, "SPEAKER_01")]
        result = helper.assign_speakers_to_segments(asr, turns)
        assert result == [
            {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00", "text": "Hello"},
            {"start": 2.0, "end": 3.0, "speaker": "SPEAKER_01", "text": "World"},
        ]


class TestMergeSpeakerBlocks:
    """Tests for merge_speaker_blocks."""

    def test_merges_consecutive_same_speaker(self):
        segs = [
            {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00", "text": "Hello"},
            {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "there"},
            {"start": 2.0, "end": 3.0, "speaker": "SPEAKER_01", "text": "Hi"},
        ]
        result = helper.merge_speaker_blocks(segs)
        assert result == [
            {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00", "text": "Hello there"},
            {"start": 2.0, "end": 3.0, "speaker": "SPEAKER_01", "text": "Hi"},
        ]


class TestFormatting:
    """Tests for timestamp + transcript formatting."""

    def test_format_timestamp(self):
        assert helper._format_timestamp(0) == "00:00:00"
        assert helper._format_timestamp(65) == "00:01:05"
        assert helper._format_timestamp(3725) == "01:02:05"

    def test_format_diarized_transcript(self):
        segs = [
            {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00", "text": "Hello"},
            {"start": 65.0, "end": 70.0, "speaker": "SPEAKER_01", "text": "Hi there"},
        ]
        text = helper.format_diarized_transcript(segs)
        assert text == "[00:00:00] SPEAKER_00: Hello\n[00:01:05] SPEAKER_01: Hi there"


class TestDiarizeAudio:
    """Tests for diarize_audio (pyannote mocked)."""

    def test_raises_without_token(self):
        # pyannote import is attempted first; patch it so the ValueError path is reached.
        fake_module = MagicMock()
        with patch.dict(sys.modules, {"pyannote": MagicMock(), "pyannote.audio": fake_module}):
            with pytest.raises(ValueError):
                helper.diarize_audio("audio.wav", hf_token=None)

    def test_returns_merged_turns(self):
        fake_pipeline = MagicMock()

        def _track(start, end, speaker):
            seg = MagicMock()
            seg.start = start
            seg.end = end
            return (seg, None, speaker)

        annotation = MagicMock()
        annotation.itertracks.return_value = [
            _track(0.0, 1.0, "SPEAKER_00"),
            _track(1.1, 2.0, "SPEAKER_00"),
            _track(2.0, 3.0, "SPEAKER_01"),
        ]
        fake_pipeline.return_value = annotation

        fake_audio_mod = MagicMock()
        fake_audio_mod.Pipeline.from_pretrained.return_value = fake_pipeline

        with patch.dict(sys.modules, {"pyannote": MagicMock(), "pyannote.audio": fake_audio_mod}):
            result = helper.diarize_audio("audio.wav", hf_token="tok", device="cpu")

        assert result == [(0.0, 2.0, "SPEAKER_00"), (2.0, 3.0, "SPEAKER_01")]
        fake_audio_mod.Pipeline.from_pretrained.assert_called_once_with(
            helper.DIARIZATION_MODEL, use_auth_token="tok"
        )


class TestHfAuthShim:
    """Tests for the huggingface_hub use_auth_token compatibility shim."""

    def test_translates_use_auth_token_to_token(self):
        import huggingface_hub

        original = huggingface_hub.hf_hub_download
        calls = {}

        def fake_download(*args, **kwargs):
            calls.update(kwargs)
            return "ok"

        try:
            huggingface_hub.hf_hub_download = fake_download
            helper._patch_pyannote_hf_auth()
            result = huggingface_hub.hf_hub_download(repo_id="r", filename="f", use_auth_token="tok")
            assert result == "ok"
            assert calls.get("token") == "tok"
            assert "use_auth_token" not in calls
        finally:
            huggingface_hub.hf_hub_download = original

    def test_torch_load_defaults_weights_only_false(self):
        import torch

        original = torch.load
        calls = {}

        def fake_load(*args, **kwargs):
            calls.update(kwargs)
            return "loaded"

        try:
            torch.load = fake_load
            helper._patch_torch_load_weights_only()
            result = torch.load("ckpt.bin")
            assert result == "loaded"
            assert calls.get("weights_only") is False
            # An explicit weights_only=None (as lightning's cloud_io._load passes) must
            # also be coerced to False.
            calls.clear()
            torch.load("ckpt.bin", weights_only=None)
            assert calls.get("weights_only") is False
            # An explicit weights_only=True must be preserved.
            calls.clear()
            torch.load("ckpt.bin", weights_only=True)
            assert calls.get("weights_only") is True
        finally:
            torch.load = original


class TestKeepAlignment:
    """Azure transcriber alignment + ambient-noise behavior."""

    @patch("helper.sr.Recognizer")
    @patch("helper.sr.AudioFile")
    def test_keep_alignment_inserts_empty_for_failures(self, mock_audio_file, mock_recognizer_class):
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.recognize_azure.side_effect = [Exception("err"), "Second"]
        mock_audio_file.return_value.__enter__ = MagicMock()
        mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)

        result = helper.transcribe_audio_segments(
            ["a.wav", "b.wav"], "k", "loc", keep_alignment=True
        )
        assert result == ["", "Second"]

    @patch("helper.sr.Recognizer")
    @patch("helper.sr.AudioFile")
    def test_adjust_noise_disabled(self, mock_audio_file, mock_recognizer_class):
        mock_recognizer = MagicMock()
        mock_recognizer_class.return_value = mock_recognizer
        mock_recognizer.recognize_azure.return_value = "Text"
        mock_audio_file.return_value.__enter__ = MagicMock()
        mock_audio_file.return_value.__exit__ = MagicMock(return_value=False)

        helper.transcribe_audio_segments(["a.wav"], "k", "loc", adjust_noise=False)
        mock_recognizer.adjust_for_ambient_noise.assert_not_called()


class TestDiarizedPipeline:
    """End-to-end diarized pipeline path with mocked diarization + transcription."""

    def test_whisper_diarized_writes_text_and_json(self, tmp_path, monkeypatch):
        input_file = tmp_path / "video.mp4"
        input_file.touch()

        mock_audio = MagicMock()
        mock_audio.__len__.return_value = 5000  # 5 s
        mock_audio.export = MagicMock()

        turns = [(0.0, 2.0, "SPEAKER_00"), (2.0, 5.0, "SPEAKER_01")]
        asr = [
            {"start": 0.0, "end": 2.0, "text": "Hello there"},
            {"start": 2.0, "end": 5.0, "text": "General Kenobi"},
        ]

        with patch("helper.is_youtube_url", return_value=False), \
             patch("helper.check_file_exists", return_value=True), \
             patch("helper.get_audio_channel", return_value=mock_audio), \
             patch("helper.diarize_audio", return_value=turns), \
             patch("helper.transcribe_whisper_with_timestamps", return_value=asr), \
             patch("helper.clean_up_temp_files"):
            full_text, output_file = helper.transcribe_pipeline(
                input_source=str(input_file),
                backend="openai-whisper",
                model_size="base",
                device="cpu",
                output_dir=str(tmp_path),
                diarize=True,
                hf_token="tok",
            )

        assert "SPEAKER_00: Hello there" in full_text
        assert "SPEAKER_01: General Kenobi" in full_text
        assert os.path.exists(output_file)

        json_path = helper.get_json_sidecar_path(str(input_file), output_dir=str(tmp_path))
        assert os.path.exists(json_path)
        data = json.loads(open(json_path, encoding="utf-8").read())
        assert data["diarized"] is True
        assert data["backend"] == "openai-whisper"
        assert data["speakers"] == ["SPEAKER_00", "SPEAKER_01"]
        assert len(data["segments"]) == 2
        # HF token must never be serialized
        assert "tok" not in json.dumps(data)

    def test_raises_when_no_speech(self, tmp_path):
        input_file = tmp_path / "video.mp4"
        input_file.touch()

        mock_audio = MagicMock()
        mock_audio.__len__.return_value = 5000
        mock_audio.export = MagicMock()

        with patch("helper.is_youtube_url", return_value=False), \
             patch("helper.check_file_exists", return_value=True), \
             patch("helper.get_audio_channel", return_value=mock_audio), \
             patch("helper.diarize_audio", return_value=[(0.0, 5.0, "SPEAKER_00")]), \
             patch("helper.transcribe_whisper_with_timestamps", return_value=[]), \
             patch("helper.clean_up_temp_files"):
            with pytest.raises(RuntimeError):
                helper.transcribe_pipeline(
                    input_source=str(input_file),
                    backend="openai-whisper",
                    device="cpu",
                    output_dir=str(tmp_path),
                    diarize=True,
                    hf_token="tok",
                )
