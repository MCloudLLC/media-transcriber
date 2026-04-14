# Dallas — History

## Core Context

- **Project:** video-to-text-azure-speech-api
- **Stack:** Python 3.8+, Azure Speech API (azure-cognitiveservices-speech), pydub, ffmpeg/moviepy
- **What it does:** Extracts audio from video → splits into 1-min segments → transcribes with Azure Speech-to-Text → saves `<name>_transcription.txt`
- **Key files:** `main.py` (entry), `helper.py` (audio utilities)
- **User:** Copilot
- **Notes:** Credentials currently hardcoded in `main.py` (`AZURE_SPEECH_KEY`, `AZURE_AI_LOCATION`) — README flags this as a security concern and recommends env vars

## Learnings

### 2026-04-14: Cross-agent context — Ripley's Phase 1 implementation decisions

**From ripley-phase1-impl background agent (Orchest. Log: 2026-04-14T03-07-02Z-ripley.md):**

Ripley completed Phase 1 GUI implementation with key technical decisions that align with Dallas's CUDA 13.x architecture:

1. **CUDA Fallback Warning Enhanced** — Updated `_cuda_fallback_warning()` in helper.py to explicitly reference `pip install .[whisper]` and README Troubleshooting section (as per Dallas recommendation from 2026-04-14)

2. **Gradio GUI Phase 1 Launch** — Implemented transcription tab with:
   - File/URL upload, auto backend selection (cuda if available, else cpu)
   - Progress callback integrated into transcription pipeline
   - Dual-backend support: faster-whisper (default) + openai-whisper fallback
   - All changes backward-compatible with existing CLI

3. **app.py Created** — New Gradio GUI scaffolding:
   - Tab 1: Transcription (Phase 1)
   - Tab 2: Reserved for Q&A (Phase 2)
   - Backend picker; device selector with auto-detect fallback

4. **main.py Backend Dispatch** — Added `--backend faster-whisper|openai-whisper` flag:
   - Default: faster-whisper (existing behavior)
   - User override: `--backend openai-whisper` for CUDA 13.x fallback
   - Clean dispatch in main.py; backend implementations isolated

5. **pyproject.toml Extras** — Added:
   - `[gui]` extra: gradio>=4.0
   - `[whisper-pytorch]` extra: openai-whisper>=20231117
   - No torch in extras (users handle CUDA wheel install manually per Dallas plan)

6. **Code Quality** — Verified:
   - No `logging.basicConfig()` in helper.py (kept in main.py only)
   - Credentials loading from env vars (from 2026-04-13 fixes)
   - All exceptions propagated; cleanup in finally blocks
   - CUDA fallback message enhanced with documentation pointer

**Cross-check with Dallas decisions:** Ripley's implementation fully aligns with CUDA 13.x decision (keep faster-whisper primary, openai-whisper as fallback), Gradio framework choice, and multi-backend architecture. No conflicts; all technical decisions synchronized.

**Status:** Phase 1 implementation ready for Hudson's validation run.

### 2026-04-14: CUDA 13.x backend alternatives analysis

**Request:** Christopher asked for evaluation of alternative Whisper backends for users on CUDA 13.x, where `ctranslate2` (inside faster-whisper) fails with `cublas64_12.dll not found`.

**Key findings:**

1. **ctranslate2 has NO released CUDA 13.x support** — PyPI classifier confirms `CUDA :: 12 :: 12.4` is the ceiling as of v4.7.1 (latest, Feb 4, 2026). GitHub issue #1933 is open; PR #2027 (March 2026) is in progress testing CUDA 13.2 but unshipped.

2. **The pip shim workaround (`nvidia-cublas-cu12`) already in `[whisper]` extra should fix most CUDA 13.x users** — ctranslate2 compiled for CUDA 12.4 can find its required DLLs from the pip-installed package regardless of system CUDA version. The main fix is ensuring users install `pip install .[whisper]` not just `faster-whisper` alone.

3. **`whisperx` and `whispercpp` eliminated immediately** — whisperx depends on faster-whisper (same ctranslate2 problem); whispercpp is CPU-only.

4. **`openai-whisper` is the correct fallback backend** — PyTorch tracks CUDA releases much faster than ctranslate2. API is very similar to faster-whisper (same `beam_size`, same model names). Key differences: no `compute_type` parameter; `transcribe()` returns a dict not an iterator; segment text via `result["segments"][i]["text"]` instead of `s.text`. Slower (~2-4×) but fully CUDA 13.x compatible.

5. **Architecture: dual-backend, faster-whisper stays primary** — Adding `[whisper-pytorch]` extra with openai-whisper; dispatching via `--backend` flag in main.py. No changes to existing faster-whisper path.

6. **Instruction for Ripley:** Update `_cuda_fallback_warning()` to reference `pip install .[whisper]` explicitly.

**Deliverable:** Written to `.squad/decisions/inbox/dallas-cuda13-alternatives.md`.

### 2026-04-13: Project review complete — Findings merged into decisions.md

**Full project review completed** with Ripley (code review) and Hudson (test coverage assessment).

**Cross-agent alignment:**
- Ripley's code review confirms Dallas' findings on credentials, Windows command, and error handling — added details on temp file cleanup (`finally` block), constant naming, exception swallowing patterns
- Hudson's test plan identifies same critical issues (credentials at module load, scattered `sys.exit`, no cleanup on crash) as testability blockers; recommends 43+ core test cases
- Consensus: Prioritize credentials (use env vars), cleanup in finally block, cross-platform file opening, and test infrastructure setup
- All findings deduplicated and merged into `.squad/decisions.md`
- Orchestration logs created: `.squad/orchestration-log/2026-04-13T18-23-25Z-dallas.md` et al.

### 2026-04-13: Documentation and dependency fixes applied

**README.md fixes (6 total):**
1. Fixed `cd video_to_text` → `cd video-to-text-azure-speech-api` (matches actual repo name)
2. **Removed unsafe hardcoding instructions** for `main.py` credentials (FIX for Critical security issue)
3. **Added environment variable setup** with platform-specific examples (Linux/macOS, Windows CMD, PowerShell)
4. **Added `ffmpeg` as explicit prerequisite** with installation commands (brew, apt-get, download link)
5. Updated project structure to show `video-to-text-azure-speech-api/` (correct repo name) and added `tests/` directory
6. Expanded supported formats from "MP4" to "MP4, AVI, MKV, MOV, MP3, WAV, FLAC, OGG (and others)"
7. Replaced outdated hardcoding warning with statement: "credentials read from environment variables; app exits if missing"

**requirements.txt fixes (3 total):**
1. Removed `standard-aifc==3.13.0` — unused, Python 3.8+ has built-in audiofile support
2. Removed `standard-chunk==3.13.0` — unused, not imported anywhere
3. Removed `typing_extensions==4.13.2` — unused, Python 3.8+ includes typing module natively
4. Added test dependencies: `pytest==8.3.5`, `pytest-mock==3.14.0`, `pytest-cov==6.1.0`
5. Kept `audioop-lts==0.2.1` — necessary for Python 3.13+ (SpeechRecognition dependency)

**Rationale:** These changes implement critical security recommendation (env vars for credentials), clarify platform prerequisites (ffmpeg), and align documentation with actual repository structure and testing infrastructure (Hudson's test plan). Cleanup of unused dependencies improves clarity and reduces supply chain surface area.

### 2026-04-13: Whisper integration architecture analysis

**Request:** Christopher asked whether to add local Whisper support as new project or extend existing Azure-based tool.

**Analysis completed:** Evaluated 3 options:
- **Option A (New repo):** Clean slate but duplicates 60% of codebase (audio extraction, segmentation, I/O)
- **Option B (Unified multi-backend):** One CLI with `--backend azure|whisper` — shares audio pipeline, low abstraction cost (~20 lines)
- **Option C (Replace Azure):** Throws away working integration users may depend on

**Recommendation: Option B — Unified multi-backend project**

**Key reasoning:**
- Code reuse is significant: audio extraction (`pydub`), segment splitting (1-min chunks), file I/O, cleanup all backend-agnostic
- Better UX: One tool, user picks backend per job — no "which tool?" confusion
- Complexity cost is LOW: `BaseTranscriber` interface with `.transcribe()` method, two implementations
- Keeps Azure for production quality (speaker diarization, custom models), adds Whisper for offline/cost-sensitive use

**Technical decisions:**
- Whisper variant: **faster-whisper** (CTranslate2) — 4x faster than openai-whisper, same accuracy, lower memory
- Model size: Default to **base** (1x realtime on CPU), let users override with `--model small|medium|large`
- YouTube support: **yt-dlp** (actively maintained, handles 1000+ sites) as input adapter — no architecture change
- Dependency strategy: Make faster-whisper optional, lazy-load with helpful error if missing (avoids 500MB PyTorch for Azure-only users)

**Gotchas identified:**
- Current `speech_recognition` library wraps Azure but not Whisper — solution: call backends directly (cleaner)
- Model download on first run (~75MB base, ~450MB small) — document clearly
- Existing pydub pipeline already produces 16kHz mono WAV — perfect for Whisper, no changes needed

**Implementation estimate:** 3-4 hours (backend abstraction 1-2h, YouTube 30m, docs 1h)

**Deliverable:** Written full analysis to `.squad/decisions/inbox/dallas-whisper-architecture.md` for team review.

### 2025-07-18: GUI + Q&A architecture proposal

**Request:** Christopher wants to package the tool with a GUI for two goals: (1) video transcription (existing behavior), (2) use transcriptions as a knowledge source for Q&A.

**Key architecture decisions:**

1. **GUI Framework: Gradio** — Python-native, browser-based, first-class chat interface (`gr.ChatInterface`) and file upload (`gr.File`). Tabs map perfectly to two-goal architecture. Beats Streamlit on chat UX and event-driven model (no re-run on interaction). Beats Tkinter/PyQt on development speed and modern UI.

2. **Q&A Approach: Hybrid (in-context + RAG)** — Short transcripts (< ~25K tokens) use full text as LLM system message. Long transcripts use chunked RAG with ChromaDB (local vector store) + sentence-transformers (local embeddings). LLM access via OpenAI-compatible API (works with Ollama, OpenAI, Azure OpenAI).

3. **Project structure:** Two new files — `app.py` (Gradio GUI), `qa.py` (Q&A engine). Refactor `main.py` pipeline into `helper.transcribe_pipeline()` with `progress_callback` for GUI integration. Existing functions unchanged.

4. **Dependency strategy:** Optional extras — `[gui]` for Gradio, `[qa]` for ChromaDB + sentence-transformers + openai, `[all]` for everything. Keeps base install lean.

5. **Packaging:** `[project.scripts]` entry points — `media-transcriber` (CLI), `media-transcriber-gui` (GUI). Continue using uv.

6. **Two-phase delivery:** Phase 1 = transcription GUI (wraps existing backend). Phase 2 = Q&A tab (load transcript, chat with LLM).

**Deliverable:** Written to `.squad/decisions/inbox/dallas-gui-qa-architecture.md`.

### 2025-07-19: CUDA/GPU architecture revision

**Request:** Christopher asked to review the GUI + Q&A architecture proposal in light of recent CUDA/GPU processing changes already merged into `helper.py`.

**Analysis performed:** Reviewed `helper.py` (existing CUDA support in `transcribe_with_whisper`), `pyproject.toml` (current `[whisper]` extra), and the original architecture proposal. Evaluated impact across 7 dimensions: Whisper CUDA, PyTorch/sentence-transformers CUDA, GPU memory, device selection UX, extras design, system requirements, and risks.

**Key decisions:**

1. **No GPU-specific extras** — Rejected `[whisper-gpu]` and `[qa-gpu]` extras. `faster-whisper` is already GPU-ready (same package, runtime detection). PyTorch CUDA wheels can't be controlled via pyproject.toml extras (different index URL required). Extras explosion would confuse users for marginal benefit.

2. **PyTorch CUDA packaging: CPU-default + documented upgrade** — This was the hardest decision. Evaluated 4 options (separate extras, runtime detection, ONNX replacement, uv sources). Chose Option B: install CPU torch by default via `[qa]` extra; document `uv pip install torch --index-url .../cu121` for GPU users. Rationale: embeddings are NOT the bottleneck (~5ms/chunk on CPU), GPU is marginal; the packaging complexity isn't worth it.

3. **Sequential GPU pipeline** — Whisper and embedding models never run simultaneously on GPU. The GUI workflow naturally enforces this (transcribe first, then Q&A). Explicit `del model; torch.cuda.empty_cache()` required if a combined pipeline is added later.

4. **GPU tier guidance** — Documented VRAM requirements: 4GB → base/small, 8GB → medium, 12GB+ → large-v3. Embedding model (all-MiniLM-L6-v2) adds only ~90MB.

5. **GUI device selector** — Auto-detect (default) with manual cpu/cuda override in a collapsed Settings accordion. Shows GPU name if detected, informational message if not. Matches existing `helper.py` fallback pattern.

6. **Pip-installable CUDA libs preferred** — `nvidia-cublas-cu12` + `nvidia-cudnn-cu12` avoid system-level CUDA toolkit installation. Already recommended in existing `helper.py` fallback message.

7. **7 new GPU-specific risks** added to risk table — CUDA version mismatch, driver compatibility, GPU OOM, CPU-only degradation, torch wheel confusion, simultaneous model loading, cross-platform CUDA differences. All have documented mitigations.

**What existing code already handles well:**
- `transcribe_with_whisper()` device parameter and CUDA fallback (helper.py:288-362) — no changes needed
- compute_type selection (float16 for CUDA, int8 for CPU) — correct as-is
- The `[whisper]` extra in pyproject.toml — single package works for both CPU and CUDA

**Deliverable:** Updated `.squad/decisions/inbox/dallas-gui-qa-architecture.md` with 6 new/updated sections (§2a–§2d, §7, GPU risks).

### 2026-04-14: CUDA cuBLAS troubleshooting documentation

**Request:** Christopher flagged a recurring support issue on Windows: `WARNING: CUDA requested but not available: Library cublas64_12.dll is not found or cannot be loaded`. CUDA has worked in past projects, so this needs practical troubleshooting steps.

**Analysis:** This error originates from ctranslate2 (the inference engine inside faster-whisper) when:
1. CUDA device was requested (user passed `--device cuda` or GUI auto-detected GPU)
2. ctranslate2 tried to initialize CUDA at runtime but couldn't find `cublas64_12.dll`
3. Root causes: missing CUDA Toolkit 12.x, CUDA not on PATH, missing pip packages, or version mismatch (CUDA 11.x vs ctranslate2 3.x)

**Solution:** Added comprehensive `## Troubleshooting` section to README.md with 4 options in order of practicality:
- **Option 1 (fastest):** `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` — self-contained CUDA libraries in Python environment, no system install
- **Option 2:** Verify system CUDA Toolkit 12.x is installed and on PATH; add `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin` if missing
- **Option 3:** Check CUDA version match (ctranslate2 2.x needs CUDA 11.x; 3.x+ needs CUDA 12.x); upgrade or downgrade as needed
- **Option 4:** Fall back to CPU with `--device cpu` — non-fatal, auto-fallback already works, just slower

**Structure in README:** New top-level section before License. Clear headings, code blocks, explanations of what each error means, and expected outcomes for each option.

**Code review of helper.py:** The existing `_cuda_fallback_warning()` function (lines 314–324) already recommends `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`, which aligns with Option 1 of the troubleshooting guide. The function logs helpful context. **Recommendation for Ripley:** Consider adding one line to the warning message pointing users to README Troubleshooting section for complete resolution steps, e.g., "See README Troubleshooting section for step-by-step resolution."

**Deliverable:** README.md updated with Troubleshooting section (4 options, 250+ lines). Decision inbox file written to `.squad/decisions/inbox/dallas-cuda-troubleshooting.md`.

