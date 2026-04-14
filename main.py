import os
import sys
import subprocess
import logging
import argparse
import helper

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    """
    CLI entry point for media-transcriber.
    Transcribes video/audio files or YouTube URLs using Azure or Whisper backends.
    """
    parser = argparse.ArgumentParser(
        description="Transcribe video/audio files or YouTube videos to text."
    )
    parser.add_argument("input", help="Path to a local video file or a YouTube URL")
    parser.add_argument(
        "--backend",
        choices=["azure", "whisper", "openai-whisper"],
        default="azure",
        help=(
            "Transcription backend: 'azure' (default, cloud), "
            "'whisper' (local, faster-whisper, CUDA 11/12), "
            "or 'openai-whisper' (local, PyTorch, CUDA 13.x compatible)"
        ),
    )
    parser.add_argument(
        "--model",
        default="base",
        help="Whisper model size: tiny, base, small, medium, large (default: base)",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cpu",
        help="Device for Whisper inference: 'cpu' (default) or 'cuda' (NVIDIA GPU)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for the transcription file (default: current working directory)",
    )
    args = parser.parse_args()

    azure_speech_key = None
    azure_ai_location = None
    if args.backend == "azure":
        azure_speech_key = os.environ.get("AZURE_SPEECH_KEY")
        azure_ai_location = os.environ.get("AZURE_AI_LOCATION")
        if not azure_speech_key or not azure_ai_location:
            logging.error("Missing required environment variables: AZURE_SPEECH_KEY and/or AZURE_AI_LOCATION")
            sys.exit(1)

    try:
        _, transcription_file = helper.transcribe_pipeline(
            input_source=args.input,
            backend=args.backend,
            model_size=args.model,
            device=args.device,
            azure_speech_key=azure_speech_key,
            azure_ai_location=azure_ai_location,
            output_dir=args.output,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as e:
        logging.error(str(e))
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        sys.exit(1)

    # Auto-open the transcription file
    if sys.platform == "win32":
        os.startfile(transcription_file)
    elif sys.platform == "darwin":
        subprocess.run(["open", transcription_file])
    else:
        subprocess.run(["xdg-open", transcription_file])


if __name__ == "__main__":
    main()