<!-- markdownlint-disable -->

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

### 2026-04-13: GUI & Q&A Feature Test Planning — 44+ scenarios cataloged

**New Features Requested:** GUI wrapper for transcription + Q&A/knowledge source against transcripts

**Test scenario catalog written to:** `.squad/decisions/inbox/hudson-gui-qa-test-scenarios.md`

**GUI Transcription Test Strategy:**
- 24 test scenarios identified (8 happy-path, 8 error, 5 UX, 3 integration)
- **Key scenarios:** File upload, progress tracking, cancellation, backend selection (Azure/Whisper), error handling (missing ffmpeg, invalid file, API failures)
- **Testing approach:** Hybrid strategy (unit tests with mocks, integration tests with real helper.py, UI automation for workflows)
- **Library recommendation:** pytest-qt (if PyQt desktop) or Playwright (if web-based GUI)
- **Coverage goal:** 80% from unit tests, 95% user flow coverage from integration+UI tests

**Q&A Knowledge Source Test Strategy:**
- 20 test scenarios identified (4 happy-path, 7 edge cases, 4 quality gates, 5 error)
- **Key scenarios:** Load transcript & ask questions, multi-turn conversation, semantic search, empty/long transcripts, LLM failures
- **Quality gates:** Factual accuracy benchmark (≥85% correct), source citation validation (95%+ accurate), relevance scoring (≥4.0/5.0)
- **Edge cases:** No relevant answer (prevent hallucination), very long transcripts (chunking strategy), transcription errors (robustness)
- **Testing challenges:** Need to mock LLM API (Azure OpenAI) to avoid cost/latency in CI — abstract LLM interface required

**Testability Requirements Flagged for Ripley:**
1. **Dependency injection:** GUI controller must take `helper` module as parameter (not import directly) for easy mocking
2. **Progress callbacks:** Add optional `progress_callback` parameter to long-running `helper.py` functions (load_audio_segments, transcribe_audio_segments)
3. **Controller/Presenter pattern:** Separate GUI widgets from business logic (create `TranscriptionController` class)
4. **Abstract LLM interface:** Create `LLMProvider` abstract base class with `MockLLMProvider` for tests
5. **Thread safety:** Use `queue.Queue` or `threading.Lock` for async GUI state management (testable with threading unit tests)
6. **Config validation:** Validate all user inputs (Azure keys, file paths) before processing — create `ConfigValidator` class

**Critical Blockers Before Test Implementation:**
- GUI framework decision needed (PyQt vs Tkinter vs web-based) — flagged for Dallas
- Q&A architecture decision needed (RAG with embeddings vs full-context LLM) — flagged for Dallas
- Scope clarification needed (batch transcription in MVP? speaker diarization?) — flagged for Dallas

**Recommended Test Library Stack:**
```
Core:        pytest 8.3.5
Mocking:     pytest-mock 3.14.0
Coverage:    pytest-cov 6.1.0
GUI:         pytest-qt 5.3.0 (desktop) OR playwright 1.40.0 (web)
LLM Mocking: pytest-vcr 1.0.2 (record/replay API calls)
Performance: pytest-benchmark 4.0.0 (Q&A latency tests)
```

**Test Development Timeline:** 15-20 days (3-4 weeks) after architecture finalized

**Key Insight:** Existing unit tests for `helper.py` remain valid — GUI just adds new calling path. Only CLI-specific tests in `test_main.py` need refactoring into `test_cli.py` (if keeping CLI option) vs `test_gui_controller.py` (new).

**Status:** Catalog ready for Dallas architecture review. Cannot write code until framework and Q&A approach decided.

### 2026-04-15: Phase 2 Q&A Tests Complete — 12 unit tests passing, app tests require manual QA

**Comprehensive test suite written for Phase 2 Q&A functionality:**

**Tests Delivered (20 total):**
- `tests/unit/test_qa.py`: **12 tests, ALL PASSING ✅**
  - Routing logic (full-context vs RAG based on 25K token threshold)
  - LLM integration (OpenAI client initialization, custom URLs, API key fallback)
  - Chunking logic (500-word chunks, 50-word overlap verification)
  - Import error handling (helpful messages with "uv sync --extra qa")
  - Edge cases (empty transcript, custom LLM URLs)
  
- `tests/unit/test_app_qa_tab.py`: **8 tests written, SKIPPED in CI** (require GUI/display server)
  - App initialization, button state management, threading, error handling
  - Cannot run in headless CI without major app.py refactoring (CustomTkinter creates real widgets on import)

**Mocking Strategy:**
- All external dependencies (`openai`, `chromadb`, `sentence_transformers`) mocked at module level
- Tests pass without installing [qa] extra
- Import mocking uses `patch.dict(sys.modules)` to avoid actual package imports

**Spec Gaps Found (documented in `.squad/decisions/inbox/hudson-phase2-tests.md`):**
1. No validation for empty transcript (accepts empty string, sends to LLM)
2. RAG setup error handling incomplete (no fallback if ChromaDB/embeddings fail)
3. No maximum token limit for full-context (may exceed model context window at 24,999 tokens)
4. No documentation for embedding model download (~90MB on first run)
5. ChromaDB in-memory collection lost on app restart (30-60s re-indexing for large transcripts)

**Test Coverage:**
- Token estimation formula: ✅ Verified
- Routing threshold (25K tokens): ✅ Tested
- Chunking algorithm: ✅ Verified exact chunk count and overlap
- LLM call parameters: ✅ All arguments verified (URL, API key, model, prompt format)
- Error handling: ✅ Import errors, empty transcripts

**Recommendations to Ripley:**
- Add empty transcript validation in `TranscriptQA.__init__`
- Add RAG setup try/except with fallback to truncated full-context
- Document LLM context window requirement (≥30K for full-context mode)
- Consider lowering RAG threshold to 20K to leave headroom for system prompt + question

**App Integration Tests:**
- Written but not executable in CI (CustomTkinter GUI dependency)
- Recommend manual QA for: button states, threading, chat history, transcript lifecycle
- Alternative: Refactor app.py for dependency injection to enable pure unit testing

**Status:** Core `qa.py` logic 100% covered. App integration requires manual QA or display server.

### 2026-04-14: VS Code Problems fix in Q&A app tests (type-safe test patterns)

- Updated `tests/unit/test_app_qa_tab.py` to use `typing.Protocol` + `typing.cast` for private `App` test access, eliminating unknown-attribute Problems without touching production code.
- Replaced direct assignment `app.root.after = ...` with `monkeypatch.setattr(..., raising=False)` and a typed callback shim to avoid method-signature/type mismatch warnings.
- Aligned tests with current `App` attribute names (`_current_transcript`, `_qa_status_label`, `_chat_box`, `_llm_key_entry`, `_llm_model_entry`) to remove stale references.
- Targeted validation passed: `uv run pytest tests/unit/test_app_qa_tab.py -q` → `8 passed`.
