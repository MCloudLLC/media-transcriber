import os
import sys
import subprocess
import logging
import argparse
import shutil
import helper

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def main():
    """
    Main function to handle the video-to-text transcription process.
    Supports local video files and YouTube URLs, with Azure or local Whisper backends.
    """
    parser = argparse.ArgumentParser(
        description="Transcribe video/audio files or YouTube videos to text."
    )
    parser.add_argument("input", help="Path to a local video file or a YouTube URL")
    parser.add_argument(
        "--backend",
        choices=["azure", "whisper"],
        default="azure",
        help="Transcription backend: 'azure' (default) or 'whisper' (local, offline)",
    )
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model size: tiny, base, small, medium, large (default: base)",
    )
    args = parser.parse_args()

    # Validate Azure credentials only when using the Azure backend
    azure_speech_key = None
    azure_ai_location = None
    if args.backend == "azure":
        azure_speech_key = os.environ.get("AZURE_SPEECH_KEY")
        azure_ai_location = os.environ.get("AZURE_AI_LOCATION")
        if not azure_speech_key or not azure_ai_location:
            logging.error("Missing required environment variables: AZURE_SPEECH_KEY and/or AZURE_AI_LOCATION")
            sys.exit(1)

    input_source = args.input
    youtube_temp_dir = None
    audio_files = []

    try:
        # Detect YouTube URL vs local file
        if helper.is_youtube_url(input_source):
            logging.info(f"YouTube URL detected: {input_source}")
            input_file = helper.download_youtube_audio(input_source)
            youtube_temp_dir = os.path.dirname(input_file)
        else:
            if not helper.check_file_exists(input_source):
                logging.error("File does not exist or the path is invalid.")
                sys.exit(1)
            input_file = input_source

        # Step 1: Extract and process the audio channel from the video
        audio = helper.get_audio_channel(input_file)
        if audio is None:
            logging.error("Failed to process the audio channel.")
            sys.exit(1)

        # Step 2: Split the audio into smaller segments if necessary
        audio_files = helper.load_audio_segments(audio)

        # Step 3: Transcribe the audio segments
        if args.backend == "whisper":
            transcribed_text = helper.transcribe_with_whisper(audio_files, model_size=args.model)
        else:
            assert azure_speech_key is not None and azure_ai_location is not None
            transcribed_text = helper.transcribe_audio_segments(
                audio_files, api_key=azure_speech_key, api_location=azure_ai_location
            )

        # Step 4: Write the transcribed text to a file
        helper.write_file(input_file, transcribed_text)

        # Step 5: Open the transcription file for editing
        transcription_file = helper.get_transcription_file(input_file)

        # Cross-platform file opener
        if sys.platform == "win32":
            os.startfile(transcription_file)
        elif sys.platform == "darwin":
            subprocess.run(["open", transcription_file])
        else:  # Linux and other Unix-like systems
            subprocess.run(["xdg-open", transcription_file])

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

    finally:
        # Clean up temporary WAV segment files
        if audio_files:
            helper.clean_up_temp_files(audio_files)
        # Clean up YouTube download directory if applicable
        if youtube_temp_dir and os.path.exists(youtube_temp_dir):
            shutil.rmtree(youtube_temp_dir, ignore_errors=True)

if __name__ == "__main__":
    main()