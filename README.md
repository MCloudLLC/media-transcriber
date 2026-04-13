# Video/Audio to Text Transcription

A flexible transcription tool that extracts audio from local video/audio files or YouTube URLs and transcribes using either Azure Speech-to-Text (cloud) or Whisper (local/offline). Results are saved to a text file and automatically opened for review.

## Features

- **Multiple Input Sources:**
  - Local video files (MP4, AVI, MKV, MOV, WebM, etc.)
  - Local audio files (MP3, WAV, FLAC, OGG, etc.)
  - YouTube URLs (audio extracted automatically via yt-dlp)

- **Dual Transcription Backends:**
  - **Azure Speech-to-Text** (cloud-based, requires API credentials, default)
  - **Whisper** (local/offline via faster-whisper, optional, no API key needed)

- **Audio Processing:**
  - Automatic 16kHz mono WAV conversion for optimal transcription quality
  - Splits long audio into 1-minute segments for efficient processing
  - Supports any audio format ffmpeg can decode

- **Convenience Features:**
  - Auto-opens transcription file on completion (cross-platform)
  - Cleans up all temporary files automatically
  - Graceful error handling with informative messages

## Prerequisites

- **Python 3.12 or higher** (Python 3.13+ recommended for full compatibility)
- **`uv` package manager** (install from https://docs.astral.sh/uv/getting-started/)
- **`ffmpeg`** (required for audio extraction):
  - **macOS:** `brew install ffmpeg`
  - **Ubuntu/Debian:** `sudo apt-get install ffmpeg`
  - **Windows:** Download from https://ffmpeg.org/download.html and add to PATH

- **Azure credentials** (only required for `--backend azure`):
  - `AZURE_SPEECH_KEY` environment variable
  - `AZURE_AI_LOCATION` environment variable

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/MCloudLLC/media-transcriber.git
   cd media-transcriber
   ```

2. Install dependencies using `uv`:
   ```bash
   uv sync
   ```

   This installs all core dependencies into a `.venv` virtual environment.

## Configuration

### Azure Credentials (Azure Backend Only)

If using `--backend azure`, set these environment variables before running:

**Linux/macOS:**
```bash
export AZURE_SPEECH_KEY="your_azure_speech_api_key"
export AZURE_AI_LOCATION="your_azure_ai_location"
```

**Windows (Command Prompt):**
```cmd
set AZURE_SPEECH_KEY=your_azure_speech_api_key
set AZURE_AI_LOCATION=your_azure_ai_location
```

**Windows (PowerShell):**
```powershell
$env:AZURE_SPEECH_KEY="your_azure_speech_api_key"
$env:AZURE_AI_LOCATION="your_azure_ai_location"
```

**Note:** Azure credentials are only required for `--backend azure`. The Whisper backend requires no credentials.

## Usage

### Basic Command Format

```bash
uv run python main.py <input> [--backend azure|whisper] [--model tiny|base|small|medium|large]
```

**Arguments:**
- `<input>` — Path to a local video/audio file OR a YouTube URL
- `--backend` — Transcription backend: `azure` (default) or `whisper`
- `--model` — Whisper model size (default: `base`, only used with `--backend whisper`)

### Examples

**Local file with Azure backend (default):**
```bash
uv run python main.py /path/to/video.mp4
```

**Local file with Whisper backend:**
```bash
uv run python main.py /path/to/video.mp4 --backend whisper
```

**Local file with specific Whisper model:**
```bash
uv run python main.py /path/to/audio.mp3 --backend whisper --model small
```

**YouTube URL:**
```bash
uv run python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ --backend whisper
```

The transcription will be saved to `<filename>_transcription.txt` in the current directory and automatically opened.

## Whisper Backend

The Whisper backend provides local, offline transcription with no API credentials required.

### Installation

Whisper is not included in the default `requirements.txt` because it has a large PyTorch dependency (~500MB). Install it separately when needed:

```bash
pip install faster-whisper
```

### Model Sizes

Whisper offers different model sizes with trade-offs between speed and accuracy:

| Model | Size  | Speed     | Accuracy | Recommended For |
|-------|-------|-----------|----------|-----------------|
| tiny  | 39MB  | Very fast | Basic    | Quick transcription, low VRAM |
| base  | 140MB | Fast      | Good     | Default, balanced |
| small | 466MB | Moderate  | Better   | High-quality transcription |
| medium| 1.5GB | Slow      | Very good| Demanding accuracy requirements |
| large | 2.9GB | Very slow | Excellent| Maximum accuracy needed |

Specify a model with `--model`:
```bash
uv run python main.py video.mp4 --backend whisper --model large
```

## Project Structure

```
media-transcriber/
├── main.py              # CLI entry point; argument parsing and orchestration
├── helper.py            # Audio processing, YouTube download, transcription backends
├── requirements.txt     # Core dependencies (pydub, yt-dlp, etc.)
├── pytest.ini           # Pytest configuration
├── README.md            # Project documentation
├── LICENSE              # MIT License
└── tests/
    ├── conftest.py      # Pytest fixtures
    ├── unit/            # Unit tests (~71 tests)
    └── integration/     # Integration tests (require Azure credentials)
```

## Running Tests

```bash
uv run python -m pytest tests/
```

For verbose output:
```bash
uv run python -m pytest tests/ -v
```

## Notes

### Supported Formats

**Video:** MP4, AVI, MKV, MOV, WebM, and others supported by ffmpeg  
**Audio:** MP3, WAV, FLAC, OGG, AAC, and others supported by ffmpeg  
**URLs:** Standard YouTube URLs (automatically detected and extracted)

### Credential Behavior

- **Azure backend:** The application requires both `AZURE_SPEECH_KEY` and `AZURE_AI_LOCATION` environment variables to be set at startup. If either is missing, the application exits with an error message.
- **Whisper backend:** No credentials required. Works completely offline once the model is downloaded.

### Temporary Files

All temporary audio files and processing artifacts are automatically cleaned up after transcription completes, or on error. No manual cleanup is needed.

## License

This project is licensed under the MIT License. See the LICENSE file for details.