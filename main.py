import os
import sys
import subprocess
import logging
import argparse
from dotenv import load_dotenv
import helper

load_dotenv()
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
        choices=["azure", "openai-whisper"],
        default="openai-whisper",
        help=(
            "Transcription backend: 'openai-whisper' (default, local, PyTorch, CUDA 13.x compatible) "
            "or 'azure' (cloud, requires AZURE_SPEECH_KEY and AZURE_AI_LOCATION)"
        ),
    )
    parser.add_argument(
        "--model",
        default="turbo",
        help="Whisper model size: tiny, base, small, medium, large, large-v2, large-v3, turbo (default: turbo)",
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        default="cuda",
        help="Device for Whisper inference: 'cuda' (default) or 'cpu'",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for the transcription file (default: current working directory)",
    )
    parser.add_argument(
        "--diarize",
        action="store_true",
        help=(
            "Enable speaker diarization (separate speakers) via pyannote.audio. "
            "Works for both backends. Requires the [diarize] extra and a HuggingFace token "
            "(--hf-token or HF_TOKEN env var). Produces a speaker-labeled, timestamped "
            "transcript plus a structured JSON sidecar for summarization."
        ),
    )
    parser.add_argument(
        "--hf-token",
        default=None,
        help="HuggingFace access token for diarization (falls back to the HF_TOKEN env var).",
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

    hf_token = None
    if args.diarize:
        hf_token = args.hf_token or os.environ.get("HF_TOKEN")
        if not hf_token:
            logging.error(
                "Diarization requires a HuggingFace token. Pass --hf-token or set HF_TOKEN. "
                "Accept the license at https://hf.co/pyannote/speaker-diarization-3.1"
            )
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
            diarize=args.diarize,
            hf_token=hf_token,
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