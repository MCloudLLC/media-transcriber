# Hudson — History

## Core Context

- **Project:** video-to-text-azure-speech-api
- **Stack:** Python 3.8+, Azure Speech API (azure-cognitiveservices-speech), pydub, ffmpeg/moviepy
- **What it does:** Extracts audio from video → splits into 1-min segments → transcribes with Azure Speech-to-Text → saves `<name>_transcription.txt`
- **Key files:** `main.py` (entry), `helper.py` (audio utilities)
- **User:** Copilot
- **Key edge cases to know about:**
  - Unsupported video formats
  - Missing/corrupted input files
  - Azure API authentication failures
  - Empty or silent audio segments
  - Partial transcription (API timeout or failure mid-way)
  - Cleanup not happening on crash (temp files left behind)

## Learnings

### 2026-04-13: Full project review complete — Test plan merged into decisions.md

**Complete squad review conducted** with Dallas (architecture) and Ripley (code quality).

**Testability blockers aligned with code review findings:**
- Dallas flagged hardcoded credentials; Hudson confirms they're read at module import time (must use `os.getenv`)
- Ripley found temp file leak in exception path; Hudson notes cleanup must be in `finally` block
- Both Dallas and Ripley identified scattered `sys.exit()` calls as testability issue; Hudson provides monkeypatch strategy

**Zero coverage baseline — 43+ core test cases identified:**
- Unit tests: `check_file_exists`, `clean_up_temp_files`, `get_audio_channel`, `load_audio_segments`, `transcribe_audio_segments`, `get_transcription_file`, `write_file`, `main()` (8 functions)
- Per-function test cases: 5–8 each, totaling 43 scenarios
- Integration tests: end-to-end (optional, requires Azure credentials + ffmpeg)

**Critical testability issues (blocking test development):**
- `os.system("start ...")` in `main()` — Windows-only, side effect, injection-prone. Flag to Dallas.
- Hardcoded placeholder credentials at module level in `main.py` (`"<your_azure_speech_api_key>"`). Should use `os.getenv`. Tests that import `main` will always see placeholders.
- No dependency injection anywhere — all external calls (`AudioSegment.from_file`, `sr.Recognizer`, `os.system`) are inline. Testable via `unittest.mock.patch` but fragile.
- `sys.exit(1)` called directly in `main()` — tests need `pytest.raises(SystemExit)`.
- Silent exception swallowing in `transcribe_audio_segments` and `write_file` — callers cannot detect total failure.

**Test infrastructure recommendations:**
- Add to requirements.txt: `pytest==8.3.5`, `pytest-mock==3.14.0`, `pytest-cov==6.1.0`
- Create: `tests/unit/` (all core tests), `tests/integration/` (marked with `@pytest.mark.integration`)

**Status:** Full test plan merged into `.squad/decisions.md` with concrete test cases per function; inbox cleared.
