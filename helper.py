import speech_recognition as sr
from pydub import AudioSegment
import os
import math
import re
import tempfile
import logging
from typing import Any, Dict, List, Optional, Tuple

# Constants
MINUTE_TO_MILLI = 60 * 1000  # Conversion factor: minutes to milliseconds
TMP_FILE_NAME = "_temp_audio"  # Temporary file prefix
SEGMENT_LENGTH = 1 * MINUTE_TO_MILLI  # Segment length in milliseconds (1 minute)

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

def transcribe_audio_segments(audio_files: List[str], api_key: str, api_location: str) -> List[str]:
    """
    Transcribes audio segments using Azure Speech-to-Text API.

    Args:
        audio_files (list): List of audio file paths to transcribe.
        api_key (str): Azure Speech API key.
        api_location (str): Azure Speech API location.

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
                recognizer.adjust_for_ambient_noise(source)
                audio_text = recognizer.record(source)
                # Recognize speech using Azure Speech-to-Text
                text = recognizer.recognize_azure(audio_text, key=api_key, location=api_location)
                txt_array.append(text)
        except Exception as e:
            logging.error(f"Error transcribing file {file}: {e}")
            failed_files.append(file)

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


def transcribe_pipeline(
    input_source: str,
    backend: str = "azure",
    model_size: str = "base",
    device: str = "cpu",
    azure_speech_key: Optional[str] = None,
    azure_ai_location: Optional[str] = None,
    output_dir: Optional[str] = None,
    progress_callback: Optional[Any] = None,
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

        if backend == "openai-whisper":
            # Whisper's transcribe() handles long audio internally via a sliding
            # 30-second window — pre-segmentation is redundant and can hurt
            # accuracy by cutting context at arbitrary boundaries.
            tmp_dir = tempfile.mkdtemp()
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
        if youtube_temp_dir and os.path.exists(youtube_temp_dir):
            shutil.rmtree(youtube_temp_dir, ignore_errors=True)
