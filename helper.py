import speech_recognition as sr
from pydub import AudioSegment
import os
import math
import re
import json
import tempfile
import logging
from typing import Any, Dict, List, Optional, Tuple

# Constants
MINUTE_TO_MILLI = 60 * 1000  # Conversion factor: minutes to milliseconds
TMP_FILE_NAME = "_temp_audio"  # Temporary file prefix
SEGMENT_LENGTH = 1 * MINUTE_TO_MILLI  # Segment length in milliseconds (1 minute)

# Diarization constants
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"
MIN_TURN_MS = 300  # Discard speaker turns shorter than this for the Azure per-turn path
MERGE_GAP_MS = 750  # Merge adjacent same-speaker turns separated by gaps up to this length

def clean_up_temp_files(files_array: List[str]) -> None:
    """
    Deletes temporary audio files created during processing.
    """
    logging.info("Cleaning up temp files.")
    for file in files_array:
        if os.path.exists(file):
            logging.info(f"Deleting file: {file}")
            try:
                os.remove(file)
            except Exception as e:
                logging.error(f"Failed to delete {file}: {e}")
    
    # Try to remove the temp directory if it's empty
    if files_array:
        temp_dir = os.path.dirname(files_array[0])
        if temp_dir and os.path.exists(temp_dir) and temp_dir != os.getcwd():
            try:
                os.rmdir(temp_dir)
                logging.info(f"Removed temp directory: {temp_dir}")
            except OSError:
                # Directory not empty or other issue - this is fine
                pass

def check_file_exists(input_file: str) -> bool:
    """
    Checks if the input file exists and prints its name and directory.

    Args:
        input_file (str): Path to the input file.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    if os.path.exists(input_file):
        file_name = os.path.basename(input_file)
        file_path = os.path.dirname(os.path.abspath(input_file))
        logging.info(f"Filename: {file_name}")
        logging.info(f"Directory: {file_path}")
        return True
    return False

def get_audio_channel(input_file: str) -> Optional[AudioSegment]:
    """
    Extracts and processes the audio channel from the input video file.

    Args:
        input_file (str): Path to the input video file.

    Returns:
        AudioSegment: Processed mono-channel audio with a sample rate of 16 kHz.
    """
    file_format = os.path.splitext(input_file)[1][1:]  # Extract file extension
    try:
        video = AudioSegment.from_file(input_file, format=file_format)
        audio = video.set_channels(1).set_frame_rate(16000).set_sample_width(2)
        return audio
    except Exception as e:
        logging.error(f"Error processing file {input_file}: {e}")
        return None

def load_audio_segments(audio_file: AudioSegment) -> List[str]:
    """
    Splits the audio file into smaller segments if it exceeds the segment length.

    Args:
        audio_file (AudioSegment): The audio file to be segmented.

    Returns:
        list: List of file paths to the exported audio segments.
    """
    audio_segments = []
    audio_length = len(audio_file)
    logging.info("Exporting to WAV file(s).")
    
    # Create a temp directory for WAV files
    tmp_dir = tempfile.mkdtemp()

    if audio_length > SEGMENT_LENGTH:
        logging.info("Audio larger than 1 minute, splitting into smaller segments.")
        num_segments = math.ceil(audio_length / SEGMENT_LENGTH)
        for i in range(num_segments):
            start_time = i * SEGMENT_LENGTH
            end_time = min((i + 1) * SEGMENT_LENGTH, audio_length)  # Ensure last segment doesn't exceed total length
            segment: AudioSegment = audio_file[start_time:end_time]  # type: ignore[assignment]
            tmp_file = os.path.join(tmp_dir, f"{TMP_FILE_NAME}_part{i + 1}.wav")
            segment.export(tmp_file, format="wav")
            audio_segments.append(tmp_file)
            logging.info(f"Created file: {tmp_file}")
    else:
        tmp_file = os.path.join(tmp_dir, f"{TMP_FILE_NAME}.wav")
        audio_file.export(tmp_file, format="wav")
        audio_segments.append(tmp_file)
        logging.info(f"Created file: {tmp_file}")

    logging.info("Export complete.")
    return audio_segments

def transcribe_audio_segments(
    audio_files: List[str],
    api_key: str,
    api_location: str,
    keep_alignment: bool = False,
    adjust_noise: bool = True,
) -> List[str]:
    """
    Transcribes audio segments using Azure Speech-to-Text API.

    Args:
        audio_files (list): List of audio file paths to transcribe.
        api_key (str): Azure Speech API key.
        api_location (str): Azure Speech API location.
        keep_alignment (bool): When True, append an empty string for any file that
            fails to transcribe so the output list stays index-aligned with the input
            (used by the diarization path to keep speaker<->text correspondence).
            When False (default), failed files are skipped.
        adjust_noise (bool): When True (default), run ambient-noise adjustment before
            recognition. Disabled for very short diarized turns where it can consume
            or distort the available speech.

    Returns:
        list: List of transcribed text segments.
    """
    txt_array = []
    failed_files = []
    logging.info("Transcribing WAV file(s).")
    recognizer = sr.Recognizer()

    for file in audio_files:
        try:
            with sr.AudioFile(file) as source:
                logging.info(f"Transcribing file: {file}")
                if adjust_noise:
                    recognizer.adjust_for_ambient_noise(source)
                audio_text = recognizer.record(source)
                # Recognize speech using Azure Speech-to-Text
                text = recognizer.recognize_azure(audio_text, key=api_key, location=api_location)
                txt_array.append(text)
        except Exception as e:
            logging.error(f"Error transcribing file {file}: {e}")
            failed_files.append(file)
            if keep_alignment:
                txt_array.append("")

    # Check if all segments failed
    if failed_files and len(failed_files) == len(audio_files):
        raise RuntimeError(f"Failed to transcribe all {len(audio_files)} audio segments. Check API credentials and network connection.")
    
    # Warn if some segments failed (partial success)
    if failed_files:
        logging.warning(f"Partial transcription: {len(failed_files)} of {len(audio_files)} segments failed.")

    logging.info("Transcription complete.")
    return txt_array

def sanitize_filename(name: str) -> str:
    """
    Sanitizes a string for safe use as a filename on any filesystem.

    Removes or replaces characters that are invalid on Windows, macOS, or Linux.
    Collapses runs of underscores/hyphens and strips leading/trailing dots and spaces.

    Args:
        name (str): The raw filename (without extension).

    Returns:
        str: A filesystem-safe filename.
    """
    # Replace common problematic characters with underscores
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Replace whitespace with underscores
    name = re.sub(r'\s+', '_', name)
    # Remove any remaining non-ASCII or control characters
    name = re.sub(r'[^\w.\-]', '', name)
    # Collapse consecutive underscores or hyphens
    name = re.sub(r'[_\-]{2,}', '_', name)
    # Strip leading/trailing dots, underscores, and spaces
    name = name.strip('._ ')
    return name or 'transcription'


def get_transcription_file(input_file: str, output_dir: Optional[str] = None) -> str:
    """
    Generates the output transcription file path.

    Args:
        input_file (str): Path to the input video file.
        output_dir (str, optional): Directory for the output file.
            Defaults to the current working directory.

    Returns:
        str: Path to the transcription file.
    """
    file_name = os.path.splitext(os.path.basename(input_file))[0]
    file_name = sanitize_filename(file_name)
    target_dir = os.path.abspath(output_dir) if output_dir else os.getcwd()
    return os.path.join(target_dir, f"{file_name}_transcription.txt")

def write_file(input_file: str, transcribed_text: List[str], output_dir: Optional[str] = None) -> None:
    """
    Writes the transcribed text to a file.

    Args:
        input_file (str): Path to the input video file.
        transcribed_text (list): List of transcribed text segments.
        output_dir (str, optional): Directory for the output file.
            Defaults to the current working directory.
    """
    logging.info("Creating transcription file.")
    txtfile_name = get_transcription_file(input_file, output_dir=output_dir)

    try:
        with open(txtfile_name, "w", encoding="utf-8") as file:
            file.write(" ".join(transcribed_text))
        logging.info(f"Transcription saved to: {txtfile_name}")
    except Exception as e:
        logging.error(f"Error writing transcription file: {e}")
        raise


_YOUTUBE_PATTERN = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?|youtu\.be/)[\w\-]+"
)


def is_youtube_url(input_source: str) -> bool:
    """
    Checks whether the given string is a YouTube URL.

    Args:
        input_source (str): The input string to check.

    Returns:
        bool: True if the string looks like a YouTube URL, False otherwise.
    """
    return bool(_YOUTUBE_PATTERN.match(input_source))


def check_whisper_model_cache(model_size: str) -> bool:
    """
    Returns True if the given openai-whisper model is already cached on disk.

    Validates by checking file presence and non-zero size. Hash verification
    is intentionally left to whisper's own downloader on first use.

    Args:
        model_size (str): Whisper model size (e.g., 'tiny', 'base', 'large-v3').

    Returns:
        bool: True if the model file exists and is non-empty in the whisper cache.
    """
    try:
        import whisper
        import urllib.parse as _urlparse
    except ImportError:
        return False

    models: Dict[str, str] = getattr(whisper, "_MODELS", {})
    url = models.get(model_size)
    if not url:
        return False

    filename = _urlparse.unquote(url.split("/")[-1])
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
    cached_path = os.path.join(cache_dir, filename)
    return os.path.exists(cached_path) and os.path.getsize(cached_path) > 0


def download_youtube_audio(url: str) -> str:
    """
    Downloads audio from a YouTube URL using yt-dlp and converts it to WAV.

    Args:
        url (str): YouTube video URL.

    Returns:
        str: Path to the downloaded WAV file.

    Raises:
        ImportError: If yt-dlp is not installed.
        Exception: If the download or conversion fails.
    """
    try:
        import yt_dlp
    except ImportError:
        raise ImportError(
            "yt-dlp is required for YouTube support. Install it with: pip install yt-dlp"
        )

    tmp_dir = tempfile.mkdtemp()
    output_template = os.path.join(tmp_dir, "%(title)s.%(ext)s")
    ydl_opts: Dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio")

        # Find the downloaded WAV file (yt-dlp may sanitize the title)
        downloaded_file = os.path.join(tmp_dir, f"{title}.wav")
        if not os.path.exists(downloaded_file):
            wav_files = [f for f in os.listdir(tmp_dir) if f.endswith(".wav")]
            if not wav_files:
                raise FileNotFoundError(f"Downloaded audio file not found in {tmp_dir}")
            downloaded_file = os.path.join(tmp_dir, wav_files[0])

        logging.info(f"Downloaded YouTube audio to: {downloaded_file}")
        return downloaded_file

    except Exception as e:
        logging.error(f"Error downloading YouTube audio: {e}")
        raise


def transcribe_with_openai_whisper(audio_files: List[str], model_size: str = "turbo", device: str = "cpu") -> List[str]:
    """
    Transcribes audio files using openai-whisper (PyTorch backend).

    Compatible with CUDA 13.x and all CUDA versions supported by PyTorch.
    Whisper handles long audio internally via a sliding 30-second window, so
    audio_files should ideally contain a single unsegmented file per source.

    Recommended model: 'turbo' — an optimised large-v3 variant with ~8x speed
    relative to large and minimal accuracy loss (requires ~6 GB VRAM).

    Args:
        audio_files (list): List of audio file paths to transcribe.
        model_size (str): Whisper model size: tiny, base, small, medium, large,
            large-v2, large-v3, turbo (default: turbo).
        device (str): Device for inference: 'cpu' or 'cuda' (default: cpu).

    Returns:
        list: List of transcribed text strings, one per input file.

    Raises:
        ImportError: If openai-whisper is not installed.
        RuntimeError: If all files fail to transcribe.
    """
    try:
        import whisper
    except ImportError:
        raise ImportError(
            "openai-whisper is required for the openai-whisper backend. "
            "Install it with: pip install '.[whisper-pytorch]'\n"
            "Then for CUDA support: pip install torch --index-url https://download.pytorch.org/whl/cu124"
        )

    import torch
    if device == "cuda" and not torch.cuda.is_available():
        logging.warning(
            "CUDA requested but torch.cuda.is_available() is False. "
            "Falling back to CPU. Verify PyTorch CUDA wheels are installed:\n"
            "  pip install torch --index-url https://download.pytorch.org/whl/cu124"
        )
        device = "cpu"

    # fp16 halves VRAM usage and speeds up inference on CUDA; always False on CPU
    fp16 = device == "cuda"

    logging.info(f"Loading openai-whisper model: {model_size} (device={device}, fp16={fp16})")
    model = whisper.load_model(model_size, device=device)

    txt_array = []
    failed_files = []
    logging.info("Transcribing with openai-whisper.")

    try:
        for file in audio_files:
            try:
                logging.info(f"Transcribing file: {file}")
                # verbose=False suppresses per-segment console output;
                # result["text"] is the canonical full transcription string.
                result = model.transcribe(file, fp16=fp16, verbose=False)
                text = result["text"].strip() if isinstance(result, dict) else ""
                txt_array.append(text)
            except Exception as e:
                logging.error(f"Error transcribing file {file}: {e}")
                failed_files.append(file)

        if failed_files and len(failed_files) == len(audio_files):
            raise RuntimeError(f"Failed to transcribe all {len(audio_files)} audio files.")
        if failed_files:
            logging.warning(f"Partial transcription: {len(failed_files)} of {len(audio_files)} files failed.")

        logging.info("Transcription complete.")
        return txt_array
    finally:
        # Unload model from GPU to free VRAM regardless of success or failure
        try:
            model.to("cpu")
        except Exception:
            pass
        del model
        if device != "cpu":
            torch.cuda.empty_cache()
            logging.info("Whisper model unloaded from GPU; CUDA cache cleared.")


def transcribe_whisper_with_timestamps(
    audio_file: str, model_size: str = "turbo", device: str = "cpu"
) -> List[Dict[str, Any]]:
    """
    Transcribes a single audio file with openai-whisper, returning timestamped segments.

    Unlike :func:`transcribe_with_openai_whisper` (which returns the full text per file),
    this returns Whisper's native segment list so speakers can later be assigned by
    timestamp overlap. The whole file is transcribed in one pass, preserving Whisper's
    30-second sliding-window context (and thus accuracy).

    Args:
        audio_file (str): Path to the audio file to transcribe.
        model_size (str): Whisper model size (default: turbo).
        device (str): 'cpu' or 'cuda' (default: cpu).

    Returns:
        list: List of {"start": float, "end": float, "text": str} segments.

    Raises:
        ImportError: If openai-whisper is not installed.
    """
    try:
        import whisper
    except ImportError:
        raise ImportError(
            "openai-whisper is required for the openai-whisper backend. "
            "Install it with: uv sync --extra whisper"
        )

    import torch
    if device == "cuda" and not torch.cuda.is_available():
        logging.warning("CUDA requested but unavailable; falling back to CPU.")
        device = "cpu"

    fp16 = device == "cuda"
    logging.info(f"Loading openai-whisper model: {model_size} (device={device}, fp16={fp16})")
    model = whisper.load_model(model_size, device=device)

    try:
        logging.info(f"Transcribing (with timestamps): {audio_file}")
        result = model.transcribe(audio_file, fp16=fp16, verbose=False)
        segments: List[Dict[str, Any]] = []
        if isinstance(result, dict):
            for seg in result.get("segments", []) or []:
                if not isinstance(seg, dict):
                    continue
                text = str(seg.get("text", "")).strip()
                if text:
                    segments.append(
                        {
                            "start": float(seg.get("start", 0.0)),
                            "end": float(seg.get("end", 0.0)),
                            "text": text,
                        }
                    )
            # Fallback: no per-segment data but we have full text
            if not segments and str(result.get("text", "")).strip():
                segments.append(
                    {"start": 0.0, "end": 0.0, "text": str(result["text"]).strip()}
                )
        return segments
    finally:
        try:
            model.to("cpu")
        except Exception:
            pass
        del model
        if device != "cpu":
            torch.cuda.empty_cache()
            logging.info("Whisper model unloaded from GPU; CUDA cache cleared.")


def _patch_pyannote_hf_auth() -> None:
    """
    Compatibility shim for pyannote.audio 3.x + huggingface_hub >= 1.0.

    pyannote 3.x calls ``hf_hub_download(use_auth_token=...)``, but huggingface_hub 1.0
    removed that parameter in favor of ``token``. This wraps ``hf_hub_download`` so the
    legacy keyword is translated, and rebinds the already-imported references inside any
    modules that did ``from huggingface_hub import hf_hub_download`` (e.g. pyannote's
    ``core.pipeline`` and ``core.model``). Idempotent.
    """
    import sys
    import functools

    try:
        import huggingface_hub
    except ImportError:  # pragma: no cover - pyannote import would have failed first
        return

    original = huggingface_hub.hf_hub_download
    if getattr(original, "_pyannote_token_shim", False):
        return  # already patched

    @functools.wraps(original)
    def _wrapper(*args: Any, **kwargs: Any):
        if "use_auth_token" in kwargs:
            token = kwargs.pop("use_auth_token")
            kwargs.setdefault("token", token)
        return original(*args, **kwargs)

    _wrapper._pyannote_token_shim = True  # type: ignore[attr-defined]

    huggingface_hub.hf_hub_download = _wrapper
    # Rebind references already imported into other modules (e.g. pyannote internals).
    # Inspect each module's real __dict__ rather than getattr(): getattr triggers lazy
    # __getattr__ machinery (e.g. transformers' lazy module aliases), which floods stderr
    # with deprecation warnings and may import unrelated submodules.
    for module in list(sys.modules.values()):
        try:
            module_dict = getattr(module, "__dict__", None)
            if module_dict is None:
                continue
            if module_dict.get("hf_hub_download", None) is original:
                module_dict["hf_hub_download"] = _wrapper
        except Exception:  # pragma: no cover - defensive
            continue


def _patch_torch_load_weights_only() -> None:
    """
    Compatibility shim for pyannote.audio 3.x + PyTorch >= 2.6.

    PyTorch 2.6 changed ``torch.load``'s default to ``weights_only=True``, which refuses
    to unpickle pyannote's Lightning checkpoints (they embed non-tensor globals such as
    ``torch.torch_version.TorchVersion`` and omegaconf containers). The pyannote models
    are fetched from gated HuggingFace repos the user explicitly authorized, so they are
    trusted: this wraps ``torch.load`` to default ``weights_only=False`` unless a caller
    explicitly requests otherwise. Idempotent.
    """
    import functools

    try:
        import torch
    except ImportError:  # pragma: no cover - pyannote import would have failed first
        return

    original = torch.load
    if getattr(original, "_pyannote_weights_only_shim", False):
        return  # already patched

    @functools.wraps(original)
    def _wrapper(*args: Any, **kwargs: Any):
        # Treat both "absent" and an explicit None (passed by lightning's cloud_io._load)
        # as "use the trusted default" so pyannote checkpoints load under PyTorch >= 2.6.
        if kwargs.get("weights_only", None) is None:
            kwargs["weights_only"] = False
        return original(*args, **kwargs)

    _wrapper._pyannote_weights_only_shim = True  # type: ignore[attr-defined]
    torch.load = _wrapper


def diarize_audio(
    wav_path: str, hf_token: Optional[str] = None, device: str = "cpu"
) -> List[Tuple[float, float, str]]:
    """
    Runs speaker diarization on a WAV file using pyannote.audio.

    Args:
        wav_path (str): Path to a 16 kHz mono WAV file.
        hf_token (str, optional): HuggingFace access token. Required: the model is gated.
        device (str): 'cpu' or 'cuda'.

    Returns:
        list: Speaker turns as (start_seconds, end_seconds, speaker_label) tuples,
            sorted by start time with adjacent same-speaker turns merged.

    Raises:
        ImportError: If pyannote.audio is not installed.
        ValueError: If no HuggingFace token is provided.
        RuntimeError: If the pipeline fails to load (bad token / unaccepted license).
    """
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        raise ImportError(
            "Diarization requires the [diarize] extra. Install with: uv sync --extra diarize"
        )

    if not hf_token:
        raise ValueError(
            "Diarization requires a HuggingFace access token. Set HF_TOKEN (or pass "
            "--hf-token) and accept the model license at "
            "https://hf.co/pyannote/speaker-diarization-3.1"
        )

    # pyannote 3.x calls hf_hub_download(use_auth_token=...), which huggingface_hub>=1.0
    # removed in favor of `token`. Install a small compatibility shim before loading.
    _patch_pyannote_hf_auth()
    # PyTorch>=2.6 defaults torch.load to weights_only=True, which rejects pyannote's
    # trusted gated checkpoints. Allow full unpickling for these authorized models.
    _patch_torch_load_weights_only()

    logging.info(f"Loading diarization pipeline: {DIARIZATION_MODEL}")
    # pyannote 3.x uses `use_auth_token`; pyannote 4.x renamed it to `token`.
    try:
        pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, use_auth_token=hf_token)
    except TypeError:
        pipeline = Pipeline.from_pretrained(DIARIZATION_MODEL, token=hf_token)
    if pipeline is None:
        raise RuntimeError(
            "Failed to load the pyannote diarization pipeline. Verify your HuggingFace "
            "token and that you've accepted the licenses for "
            "'pyannote/speaker-diarization-3.1' and 'pyannote/segmentation-3.0'."
        )

    try:
        import torch
        if device == "cuda" and torch.cuda.is_available():
            pipeline.to(torch.device("cuda"))
            logging.info("Diarization pipeline moved to CUDA.")
    except Exception as e:  # pragma: no cover - defensive
        logging.warning(f"Could not move diarization pipeline to {device}: {e}")

    logging.info("Running speaker diarization...")
    diarization = pipeline(wav_path)

    turns: List[Tuple[float, float, str]] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        turns.append((float(turn.start), float(turn.end), str(speaker)))
    turns.sort(key=lambda t: t[0])
    merged = _merge_turns(turns, max_gap=MERGE_GAP_MS / 1000.0)
    logging.info(
        f"Diarization complete: {len(merged)} turn(s), "
        f"{len({t[2] for t in merged})} speaker(s)."
    )
    return merged


def _merge_turns(
    turns: List[Tuple[float, float, str]], max_gap: float = MERGE_GAP_MS / 1000.0
) -> List[Tuple[float, float, str]]:
    """Merges consecutive turns from the same speaker separated by gaps <= max_gap."""
    merged: List[Tuple[float, float, str]] = []
    for start, end, speaker in turns:
        if merged and merged[-1][2] == speaker and start - merged[-1][1] <= max_gap:
            prev_start, prev_end, prev_speaker = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end), prev_speaker)
        else:
            merged.append((start, end, speaker))
    return merged


def split_audio_on_turns(
    audio: AudioSegment, turns: List[Tuple[float, float, str]], tmp_dir: str
) -> List[str]:
    """
    Exports one WAV file per speaker turn (used by the Azure diarization path).

    Args:
        audio (AudioSegment): The full processed audio.
        turns (list): Speaker turns as (start, end, speaker) in seconds.
        tmp_dir (str): Directory to write the per-turn WAV files into.

    Returns:
        list: Paths to the exported per-turn WAV files, aligned with ``turns``.
    """
    paths: List[str] = []
    for i, (start, end, _speaker) in enumerate(turns):
        segment: AudioSegment = audio[int(start * 1000):int(end * 1000)]  # type: ignore[assignment]
        tmp_file = os.path.join(tmp_dir, f"{TMP_FILE_NAME}_turn{i + 1}.wav")
        segment.export(tmp_file, format="wav")
        paths.append(tmp_file)
    return paths


def _best_overlap_speaker(
    start: float, end: float, turns: List[Tuple[float, float, str]], default: str = "UNKNOWN"
) -> str:
    """Returns the speaker whose turn overlaps [start, end] the most."""
    best_speaker = default
    best_overlap = 0.0
    for t_start, t_end, speaker in turns:
        overlap = min(end, t_end) - max(start, t_start)
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = speaker
    return best_speaker


def assign_speakers_to_segments(
    asr_segments: List[Dict[str, Any]], turns: List[Tuple[float, float, str]]
) -> List[Dict[str, Any]]:
    """
    Assigns a speaker label to each ASR segment by maximum timestamp overlap.

    Args:
        asr_segments (list): [{"start", "end", "text"}] segments from the transcriber.
        turns (list): Diarization turns as (start, end, speaker) in seconds.

    Returns:
        list: [{"start", "end", "speaker", "text"}] segments.
    """
    result: List[Dict[str, Any]] = []
    for seg in asr_segments:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        speaker = _best_overlap_speaker(
            float(seg.get("start", 0.0)), float(seg.get("end", 0.0)), turns
        )
        result.append(
            {
                "start": float(seg.get("start", 0.0)),
                "end": float(seg.get("end", 0.0)),
                "speaker": speaker,
                "text": text,
            }
        )
    return result


def merge_speaker_blocks(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merges consecutive segments from the same speaker into a single block."""
    merged: List[Dict[str, Any]] = []
    for seg in segments:
        if merged and merged[-1]["speaker"] == seg["speaker"]:
            merged[-1]["end"] = seg["end"]
            merged[-1]["text"] = f"{merged[-1]['text']} {seg['text']}".strip()
        else:
            merged.append(dict(seg))
    return merged


def _format_timestamp(seconds: float) -> str:
    """Formats a number of seconds as HH:MM:SS."""
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_diarized_transcript(segments: List[Dict[str, Any]]) -> str:
    """
    Renders speaker-labeled, timestamped transcript text suitable for summarization.

    Each line: ``[HH:MM:SS] SPEAKER_00: text``
    """
    lines = [
        f"[{_format_timestamp(seg['start'])}] {seg['speaker']}: {seg['text']}"
        for seg in segments
    ]
    return "\n".join(lines)


def get_json_sidecar_path(input_file: str, output_dir: Optional[str] = None) -> str:
    """Returns the path of the JSON sidecar next to the transcription text file."""
    txt_path = get_transcription_file(input_file, output_dir=output_dir)
    return os.path.splitext(txt_path)[0] + ".json"


def write_json_sidecar(
    input_file: str, payload: Dict[str, Any], output_dir: Optional[str] = None
) -> str:
    """
    Writes a structured JSON sidecar (segments + metadata) for downstream summarization.

    Args:
        input_file (str): Source media path (used to derive the output filename).
        payload (dict): Structured transcript data. Must not contain secrets.
        output_dir (str, optional): Output directory.

    Returns:
        str: Path to the JSON file written.
    """
    json_path = get_json_sidecar_path(input_file, output_dir=output_dir)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logging.info(f"Structured transcript saved to: {json_path}")
    return json_path


def _diarize_and_transcribe(
    audio: AudioSegment,
    full_wav: str,
    backend: str,
    model_size: str,
    device: str,
    hf_token: Optional[str],
    azure_speech_key: Optional[str],
    azure_ai_location: Optional[str],
    tmp_dir: str,
) -> List[Dict[str, Any]]:
    """
    Produces speaker-labeled segments for the diarization path.

    Whisper: transcribe the full audio once (preserving context), then assign speakers
    by timestamp overlap. Azure: diarize then transcribe each turn (no timestamps
    otherwise), keeping speaker<->text alignment.

    Returns:
        list: [{"start", "end", "speaker", "text"}] blocks (consecutive same-speaker merged).
    """
    turns = diarize_audio(full_wav, hf_token=hf_token, device=device)
    if not turns:
        logging.warning("Diarization detected no speaker turns; treating audio as a single speaker.")
        turns = [(0.0, len(audio) / 1000.0, "SPEAKER_00")]

    if backend == "openai-whisper":
        asr_segments = transcribe_whisper_with_timestamps(full_wav, model_size=model_size, device=device)
        if not asr_segments:
            raise RuntimeError("Whisper produced no transcribable speech for diarization.")
        segments = assign_speakers_to_segments(asr_segments, turns)
    else:  # azure
        assert azure_speech_key is not None and azure_ai_location is not None
        usable_turns = [t for t in turns if (t[1] - t[0]) * 1000 >= MIN_TURN_MS] or turns
        if len(usable_turns) > 500:
            logging.warning(
                f"Diarization produced {len(usable_turns)} turns; transcribing each via Azure "
                "may be slow and costly."
            )
        turn_wavs = split_audio_on_turns(audio, usable_turns, tmp_dir)
        texts = transcribe_audio_segments(
            turn_wavs,
            api_key=azure_speech_key,
            api_location=azure_ai_location,
            keep_alignment=True,
            adjust_noise=False,
        )
        segments = [
            {"start": s, "end": e, "speaker": spk, "text": txt.strip()}
            for (s, e, spk), txt in zip(usable_turns, texts)
            if txt and txt.strip()
        ]

    segments = [s for s in segments if s["text"]]
    if not segments:
        raise RuntimeError(
            "Diarization produced no transcribable speech. Check the audio and credentials."
        )
    return merge_speaker_blocks(segments)


def transcribe_pipeline(
    input_source: str,
    backend: str = "azure",
    model_size: str = "base",
    device: str = "cpu",
    azure_speech_key: Optional[str] = None,
    azure_ai_location: Optional[str] = None,
    output_dir: Optional[str] = None,
    progress_callback: Optional[Any] = None,
    diarize: bool = False,
    hf_token: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Full transcription pipeline: source detection → audio extraction → segmentation →
    backend dispatch → file writing.

    Args:
        input_source (str): Local file path or YouTube URL.
        backend (str): 'azure', 'whisper', or 'openai-whisper'.
        model_size (str): Whisper model size (only used for whisper backends).
        device (str): 'cpu' or 'cuda' (only used for whisper backends).
        azure_speech_key (str, optional): Azure Speech API key (required for azure backend).
        azure_ai_location (str, optional): Azure region (required for azure backend).
        output_dir (str, optional): Output directory for transcript file.
        progress_callback (callable, optional): Called with (step: int, total: int, message: str).
            CLI passes None; GUI passes a progress updater.
        diarize (bool): When True, run speaker diarization (pyannote.audio) and produce a
            speaker-labeled, timestamped transcript plus a structured JSON sidecar.
        hf_token (str, optional): HuggingFace token (required when diarize is True).

    Returns:
        Tuple[str, str]: (full_transcript_text, output_file_path)

    Raises:
        ValueError: If Azure backend is selected without credentials.
        RuntimeError: On transcription failure.
    """
    import shutil

    def _progress(step: int, total: int, message: str) -> None:
        logging.info(f"[{step}/{total}] {message}")
        if progress_callback is not None:
            try:
                progress_callback(step, total, message)
            except Exception:
                pass

    total_steps = 5
    youtube_temp_dir = None
    audio_files: List[str] = []
    temp_dirs: List[str] = []

    try:
        # Step 1: Validate credentials for Azure backend
        _progress(1, total_steps, "Validating configuration...")
        if backend == "azure":
            if not azure_speech_key or not azure_ai_location:
                raise ValueError(
                    "Azure backend requires AZURE_SPEECH_KEY and AZURE_AI_LOCATION environment variables."
                )

        # Step 2: Resolve input source
        _progress(2, total_steps, "Resolving input source...")
        if is_youtube_url(input_source):
            logging.info(f"YouTube URL detected: {input_source}")
            input_file = download_youtube_audio(input_source)
            youtube_temp_dir = os.path.dirname(input_file)
        else:
            if not check_file_exists(input_source):
                raise FileNotFoundError(f"File does not exist: {input_source}")
            input_file = input_source

        # Step 3: Extract and process audio
        _progress(3, total_steps, "Extracting and processing audio...")
        audio = get_audio_channel(input_file)
        if audio is None:
            raise RuntimeError("Failed to process the audio channel.")

        # Diarization path: produce a speaker-labeled, timestamped transcript + JSON sidecar.
        if diarize:
            tmp_dir = tempfile.mkdtemp()
            temp_dirs.append(tmp_dir)
            full_wav = os.path.join(tmp_dir, f"{TMP_FILE_NAME}_full.wav")
            audio.export(full_wav, format="wav")
            audio_files = [full_wav]

            _progress(4, total_steps, f"Diarizing and transcribing with {backend} backend...")
            segments = _diarize_and_transcribe(
                audio=audio,
                full_wav=full_wav,
                backend=backend,
                model_size=model_size,
                device=device,
                hf_token=hf_token,
                azure_speech_key=azure_speech_key,
                azure_ai_location=azure_ai_location,
                tmp_dir=tmp_dir,
            )
            # Per-turn WAVs (Azure path) live in tmp_dir and are cleaned via temp_dirs.
            audio_files = [
                os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir)
            ]

            _progress(5, total_steps, "Writing transcription files...")
            full_text = format_diarized_transcript(segments)
            output_file = get_transcription_file(input_file, output_dir=output_dir)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(full_text)
            logging.info(f"Transcription saved to: {output_file}")
            write_json_sidecar(
                input_file,
                {
                    "source": os.path.basename(input_file),
                    "backend": backend,
                    "diarized": True,
                    "speakers": sorted({s["speaker"] for s in segments}),
                    "segments": segments,
                    "text": full_text,
                },
                output_dir=output_dir,
            )
            return full_text, output_file

        if backend == "openai-whisper":
            # Whisper's transcribe() handles long audio internally via a sliding
            # 30-second window — pre-segmentation is redundant and can hurt
            # accuracy by cutting context at arbitrary boundaries.
            tmp_dir = tempfile.mkdtemp()
            temp_dirs.append(tmp_dir)
            tmp_wav = os.path.join(tmp_dir, f"{TMP_FILE_NAME}.wav")
            audio.export(tmp_wav, format="wav")
            audio_files = [tmp_wav]
        else:
            audio_files = load_audio_segments(audio)

        # Step 4: Transcribe
        _progress(4, total_steps, f"Transcribing with {backend} backend...")
        if backend == "openai-whisper":
            transcribed_parts = transcribe_with_openai_whisper(audio_files, model_size=model_size, device=device)
        else:  # azure
            assert azure_speech_key is not None and azure_ai_location is not None
            transcribed_parts = transcribe_audio_segments(
                audio_files, api_key=azure_speech_key, api_location=azure_ai_location
            )

        # Step 5: Write output
        _progress(5, total_steps, "Writing transcription file...")
        write_file(input_file, transcribed_parts, output_dir=output_dir)
        output_file = get_transcription_file(input_file, output_dir=output_dir)
        full_text = "\n\n".join(transcribed_parts)

        return full_text, output_file

    finally:
        if audio_files:
            clean_up_temp_files(audio_files)
        for d in temp_dirs:
            if d and os.path.exists(d):
                shutil.rmtree(d, ignore_errors=True)
        if youtube_temp_dir and os.path.exists(youtube_temp_dir):
            shutil.rmtree(youtube_temp_dir, ignore_errors=True)
