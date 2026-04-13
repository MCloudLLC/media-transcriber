# Dallas — History

## Core Context

- **Project:** video-to-text-azure-speech-api
- **Stack:** Python 3.8+, Azure Speech API (azure-cognitiveservices-speech), pydub, ffmpeg/moviepy
- **What it does:** Extracts audio from video → splits into 1-min segments → transcribes with Azure Speech-to-Text → saves `<name>_transcription.txt`
- **Key files:** `main.py` (entry), `helper.py` (audio utilities)
- **User:** Copilot
- **Notes:** Credentials currently hardcoded in `main.py` (`AZURE_SPEECH_KEY`, `AZURE_AI_LOCATION`) — README flags this as a security concern and recommends env vars

## Learnings

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

