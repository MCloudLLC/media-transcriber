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
  - **OpenAI-Whisper** (local/offline via openai-whisper + PyTorch, CUDA 13.x compatible)

- **Audio Processing:**
  - Automatic 16kHz mono WAV conversion for optimal transcription quality
  - Splits long audio into 1-minute segments for efficient processing
  - Supports any audio format ffmpeg can decode

- **Convenience Features:**
  - Auto-opens transcription file on completion (cross-platform)
  - Cleans up all temporary files automatically
  - Graceful error handling with informative messages

## Prerequisites

- **Python 3.10 or higher** (Python 3.12+ recommended for full compatibility)
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

   This installs all core dependencies and dev tools (pytest) into a `.venv` virtual environment.

   To also install the optional Whisper backend:
   ```bash
   uv sync --extra whisper
   ```

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
uv run python main.py <input> [--backend azure|whisper|openai-whisper] [--model tiny|base|small|medium|large]
```

**Arguments:**
- `<input>` — Path to a local video/audio file OR a YouTube URL
- `--backend` — Transcription backend: `azure` (default), `whisper`, or `openai-whisper`
- `--model` — Whisper model size (default: `base`, only used with `--backend whisper` or `--backend openai-whisper`)

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

**CUDA 13.x users (RTX 50-series):**
```bash
uv run python main.py /path/to/video.mp4 --backend openai-whisper --device cuda
```

**YouTube URL:**
```bash
uv run python main.py https://www.youtube.com/watch?v=dQw4w9WgXcQ --backend whisper
```

The transcription will be saved to `<filename>_transcription.txt` in the current directory and automatically opened.

## Whisper Backend

The Whisper backend provides local, offline transcription with no API credentials required.

### Installation

Whisper is not included in the default install because it has a large PyTorch dependency (~500MB). Install it as an optional extra when needed:

```bash
uv sync --extra whisper
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

## Desktop GUI (CustomTkinter)

A native desktop GUI is available for easier use without the command line.

### Installation

Install the GUI extra:
```bash
uv sync --extra gui
```

Or install everything at once:
```bash
uv sync --extra all
```

### Running the GUI

```bash
uv run media-transcriber-gui
```

Or directly:
```bash
uv run python app.py
```

Opens a native desktop window — no browser required.

### GUI Features

- Browse local video/audio files or paste a YouTube URL
- Select backend: **Whisper** (fast, CUDA 11/12), **OpenAI-Whisper** (CUDA 13.x), or **Azure**
- Choose Whisper model size and device (CPU or CUDA GPU)
- Real-time progress display
- Copyable transcription output with Save As dialog

### Q&A (Ask questions about your transcript)

After transcribing, switch to the **Q&A** tab.

Requires a local LLM (Ollama recommended):
1. `uv sync --extra qa`
2. Install Ollama: https://ollama.ai
3. `ollama pull llama3`
4. Transcribe a file, then ask questions in the Q&A tab

The LLM URL, API key, and model are configurable in the Q&A tab.
Works with any OpenAI-compatible endpoint (OpenAI, LM Studio, etc.).

## Project Structure

```
media-transcriber/
├── main.py              # CLI entry point; argument parsing and orchestration
├── app.py               # Desktop GUI entry point (CustomTkinter)
├── helper.py            # Audio processing, YouTube download, transcription backends
├── pyproject.toml       # Project metadata and dependencies (uv)
├── uv.lock              # Locked dependency versions
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

## Troubleshooting

### CUDA: `cublas64_12.dll` not found

**Error:** `WARNING: CUDA requested but not available: Library cublas64_12.dll is not found or cannot be loaded`

**What it means:** You requested GPU acceleration for Whisper transcription, but the system cannot find the cuBLAS library that ctranslate2 (the inference engine) needs at runtime. This typically means CUDA 12.x libraries are not available on your system PATH.

**Resolution (try in order):**

#### Option 1: Install CUDA libraries via pip (fastest, no system install needed)

This approach installs self-contained CUDA runtime libraries into your Python environment. No system-wide CUDA Toolkit installation required.

```bash
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

Or with `uv`:

```bash
uv pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

Then run your transcription again. ctranslate2 will auto-detect these libraries in your Python environment.

#### Option 2: Verify CUDA Toolkit 12.x is installed and on PATH

1. **Check if GPU is visible:**
   ```bash
   nvidia-smi
   ```
   Should list your GPU(s). If command not found, you may not have NVIDIA drivers installed.

2. **Check CUDA Toolkit version:**
   ```bash
   nvcc --version
   ```
   Should show CUDA 12.x. If it shows CUDA 11.x or command not found, see the version mismatch section below.

3. **If CUDA 12.x is installed but DLL still not found:**
   - The CUDA binaries folder is not on your system PATH
   - Add `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin` to your system PATH
   - Restart your terminal after changing PATH
   - Verify: `echo %PATH%` (Windows CMD) or `$env:PATH` (PowerShell) should include the CUDA bin directory

#### Option 3: Resolve CUDA version mismatch

Different versions of ctranslate2 require different CUDA versions:
- **ctranslate2 2.x** requires CUDA 11.x
- **ctranslate2 3.x+** requires CUDA 12.x

**Check your ctranslate2 version:**
```bash
python -c "import ctranslate2; print(ctranslate2.__version__)"
```

**If you have CUDA 11.x but need CUDA 12.x:**
- Option A: Upgrade to CUDA Toolkit 12.x (visit https://developer.nvidia.com/cuda-toolkit)
- Option B: Use faster-whisper with an older version that bundles ctranslate2 2.x (not recommended; pin versions carefully)

**If you have CUDA 12.x but ctranslate2 still fails:**
- Try Option 1 (pip install nvidia-cublas-cu12) — often resolves library path issues even with system CUDA

#### Option 4: Fall back to CPU (no GPU needed)

GPU acceleration is optional. If you don't need GPU performance or can't get CUDA working:

```bash
uv run python main.py /path/to/video.mp4 --backend whisper --device cpu
```

Or in the GUI, select **Device: CPU** in Settings.

**Note:** The warning message is non-fatal — ctranslate2 automatically falls back to CPU when it cannot initialize CUDA. Transcription will complete, just slower. A typical video takes 1–3 minutes per minute of audio on CPU (varies by model and hardware).

### CUDA 13.x / Blackwell GPUs (RTX 50-series)

If you have CUDA 13.x installed and faster-whisper fails with `cublas64_12.dll not found`:

**Step 1: Try the pip CUDA shim fix**

faster-whisper requires CUDA 12.x libraries. Installing the full `[whisper]` extra provides them automatically:

```bash
uv sync --extra whisper
```

This installs `nvidia-cublas-cu12` and `nvidia-cudnn-cu12` into your Python environment — ctranslate2 finds them automatically without system-wide CUDA changes.

**Step 2: If Step 1 doesn't resolve it — use the PyTorch backend**

`openai-whisper` uses PyTorch which tracks new CUDA releases much faster:

```bash
uv pip install ".[whisper-pytorch]"
# Then install CUDA-enabled PyTorch:
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

Run with:
```bash
uv run python main.py video.mp4 --backend openai-whisper --device cuda
```

**Note:** `openai-whisper` is 2–3× slower than `faster-whisper` on the same GPU. Once ctranslate2 ships CUDA 13.x support, you can switch back to `--backend whisper`.

**Track ctranslate2 CUDA 13.x support:** https://github.com/OpenNMT/CTranslate2/issues/1933

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.