import speech_recognition as sr
from pydub import AudioSegment
import os
import math
import re
import tempfile
import logging
from typing import List, Optional, Tuple

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
            segment = audio_file[start_time:end_time]
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

def get_transcription_file(input_file: str) -> str:
    """
    Generates the output transcription file path.

    Args:
        input_file (str): Path to the input video file.

    Returns:
        str: Path to the transcription file.
    """
    file_name = os.path.splitext(os.path.basename(input_file))[0]
    file_path = os.path.dirname(os.path.abspath(input_file))
    return os.path.join(file_path, f"{file_name}_transcription.txt")

def write_file(input_file: str, transcribed_text: List[str]) -> None:
    """
    Writes the transcribed text to a file.

    Args:
        input_file (str): Path to the input video file.
        transcribed_text (list): List of transcribed text segments.
    """
    logging.info("Creating transcription file.")
    txtfile_name = get_transcription_file(input_file)

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
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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


def transcribe_with_whisper(audio_files: List[str], model_size: str = "base") -> List[str]:
    """
    Transcribes audio segments using a local Whisper model via faster-whisper.

    Args:
        audio_files (list): List of audio file paths to transcribe.
        model_size (str): Whisper model size: tiny, base, small, medium, large (default: base).

    Returns:
        list: List of transcribed text segments.

    Raises:
        ImportError: If faster-whisper is not installed.
        RuntimeError: If all segments fail to transcribe.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ImportError(
            "faster-whisper is required for the Whisper backend. "
            "Install it with: pip install faster-whisper"
        )

    logging.info(f"Loading Whisper model: {model_size}")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    txt_array = []
    failed_files = []
    logging.info("Transcribing WAV file(s) with Whisper.")

    for file in audio_files:
        try:
            logging.info(f"Transcribing file: {file}")
            segments, _ = model.transcribe(file, beam_size=5)
            text = " ".join(segment.text.strip() for segment in segments)
            txt_array.append(text)
        except Exception as e:
            logging.error(f"Error transcribing file {file}: {e}")
            failed_files.append(file)

    if failed_files and len(failed_files) == len(audio_files):
        raise RuntimeError(
            f"Failed to transcribe all {len(audio_files)} audio segments."
        )

    if failed_files:
        logging.warning(
            f"Partial transcription: {len(failed_files)} of {len(audio_files)} segments failed."
        )

    logging.info("Transcription complete.")
    return txt_array
