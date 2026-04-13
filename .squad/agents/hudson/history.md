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

### 2026-04-13: Complete test infrastructure scaffolded — All unit and integration tests written

**Test infrastructure created:**
- Directory structure: `tests/unit/`, `tests/integration/` with proper `__init__.py` files
- Configuration: `pytest.ini` at repo root with markers for integration and slow tests
- Shared fixtures: `conftest.py` with `tmp_wav_file`, `mock_audio_segment`, and `azure_env_vars` fixtures

**Unit tests written (8 modules, 55+ test cases):**
- `test_check_file_exists.py`: 4 tests covering file existence, missing files, empty strings, and logging verification
- `test_clean_up_temp_files.py`: 4 tests covering deletion, missing files, empty lists, and partial deletes
- `test_get_audio_channel.py`: 6 tests covering AudioSegment chain calls, exceptions, format extraction, and audio settings (mono, 16kHz, 16-bit)
- `test_load_audio_segments.py`: 6 tests covering short/long audio splitting, edge cases (exactly 1 minute), temp dir usage, return types, and unique naming
- `test_transcribe_audio_segments.py`: 9 tests covering single/multi-file transcription, total/partial failures, API parameter passing, empty lists, and ambient noise adjustment
- `test_get_transcription_file.py`: 5 tests covering path generation, spaces in names, missing extensions, multiple dots, and absolute paths
- `test_write_file.py`: 5 tests covering file writing, error propagation (not swallowing), path usage, empty lists, and UTF-8 encoding
- `test_main.py`: 13 tests covering no args, missing files, audio extraction failure, cleanup in finally block, missing env vars, platform-specific file openers (Windows/macOS/Linux), and full happy path

**Integration tests written:**
- `test_end_to_end.py`: 3 tests marked with `@pytest.mark.integration` and skipif guards for missing Azure credentials
- Real Azure API transcription test (with cost warning in docstring)
- File handling and transcription file write/read verification

**Mock patterns used:**
- `unittest.mock.patch` for external dependencies (AudioSegment, sr.Recognizer, file I/O)
- `MagicMock` for object behavior simulation (AudioSegment slicing, export methods)
- `monkeypatch` for environment variables and sys.argv
- `tmp_path` fixture for real file system operations without polluting repo
- Platform detection mocking for cross-platform file opener tests

**Key testing strategies:**
- All Azure API calls mocked in unit tests (no real API calls)
- File system operations use pytest's `tmp_path` fixture
- Audio library (pydub) fully mocked with behavioral stubs
- Environment variables isolated per test with `monkeypatch`
- Integration tests properly guarded with `pytest.mark.skipif` for missing credentials

**Mock targets identified:**
- `helper.AudioSegment` and `helper.AudioSegment.from_file` for audio loading
- `helper.sr.Recognizer` and `helper.sr.AudioFile` for speech recognition
- `helper.tempfile.mkdtemp` for temp directory creation
- `helper.logging` for log output verification
- `main.sys.argv`, `main.sys.exit`, `main.sys.platform` for CLI and platform behavior
- `main.os.startfile` and `main.subprocess.run` for file opening

**Coverage expectations:**
- All 7 helper.py functions covered
- main.py execution flow covered (happy path and all error paths)
- Edge cases: empty inputs, partial failures, missing files, platform variations
- Error propagation verified (no silent swallowing)

**Test execution instructions:**
- Run all tests: `pytest`
- Run unit tests only: `pytest tests/unit/`
- Skip integration tests: `pytest -m "not integration"`
- Run with coverage: `pytest --cov=. --cov-report=html`

**Issues discovered during test writing:**
- None — tests written against expected post-fix behavior per charter
- All tests will initially fail until Ripley's refactoring is complete
- Tests serve as specification for correct behavior
