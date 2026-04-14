# Ripley — History

## Core Context

- **Project:** video-to-text-azure-speech-api
- **Stack:** Python 3.8+, Azure Speech API (azure-cognitiveservices-speech), pydub, ffmpeg/moviepy
- **What it does:** Extracts audio from video → splits into 1-min segments → transcribes with Azure Speech-to-Text → saves `<name>_transcription.txt`
- **Key files:** `main.py` (entry), `helper.py` (audio utilities)
- **User:** Copilot
- **Notes:** Credentials currently hardcoded in `main.py` (`AZURE_SPEECH_KEY`, `AZURE_AI_LOCATION`) — README flags this as a security concern and recommends env vars
- **Audio segmentation:** Default 1-minute segments, configurable
- **Cleanup:** Temporary audio files deleted after transcription

## Learnings

### 2026-04-13 — Full project review complete; findings merged into decisions.md

Complete code review of `main.py` and `helper.py` conducted with Dallas (architecture) and Hudson (test coverage).

**Critical findings synchronized:**
- Dallas identified same hardcoded credentials, Windows-only command — added details on env var migration, README contradictions
- Hudson flagged credentials at module import time as testability blocker; recommends env var loading before `main()` calls
- Consensus on exception handling: use `finally` block for cleanup, re-raise exceptions instead of swallowing

**Additional code-specific issues:**
- **`SECOND_TO_MILLI`** is misnamed — value is `60 * 1000 = 60 000`, which is minutes-to-milliseconds, not seconds-to-milliseconds. Should be `MINUTE_TO_MILLI`.
- **Temp file leak pattern:** `clean_up_temp_files` must be in a `finally` block, not the happy-path only, to avoid leaving WAV segments on disk after a crash.
- **`write_file` swallows exceptions** — it prints but does not raise, so callers never know a write failed.
- **`os.system("start ...")` is Windows-only** and breaks on paths with spaces. Use `os.startfile()` on Windows, `subprocess.run(["open", ...])` on macOS, `subprocess.run(["xdg-open", ...])` on Linux.
- **`recognize_azure` `location` kwarg** is not in SpeechRecognition's documented public API — may be silently ignored or raise `TypeError`. Needs runtime verification or switch to `azure-cognitiveservices-speech` SDK.
- **Credentials are hardcoded** in `main.py` — should use `os.environ.get()` with a startup guard.
- **`print()` throughout** — should use `logging` module for production-quality diagnostic output.
- **No type hints** despite `typing_extensions` being in requirements.txt.
- **`typing_extensions`** is listed as a dependency but not imported anywhere — dead dependency.
- **Temp WAV files** written to CWD rather than a proper temp directory (`tempfile.mkdtemp`).

**Status:** All findings merged into `.squad/decisions.md`; inbox cleared.

### 2026-04-13 — All 10 Code Fixes Implemented

Completed implementation of all critical, high, and medium severity fixes identified in team code review.

**Key Implementation Decisions:**

1. **`recognize_azure` Return Value Discovery**
   - Investigated SpeechRecognition library behavior
   - **Finding:** Default `recognize_azure(show_all=False)` returns single `str`, NOT tuple `(text, confidence)`
   - **Fix:** Changed from tuple unpacking to single value assignment: `text = recognizer.recognize_azure(...)`
   - Previous code would have raised `TypeError` on every transcription attempt
   - Confirmed `location` parameter IS supported in the API signature

2. **Tempfile Strategy**
   - Chose `tempfile.mkdtemp()` over UUID/timestamp-prefixed files in CWD
   - **Rationale:** Prevents concurrent run collisions, follows OS conventions, enables clean directory removal
   - Implementation: `tmp_dir = tempfile.mkdtemp()` → write WAV files to `os.path.join(tmp_dir, filename)`
   - Cleanup: `clean_up_temp_files()` removes files then attempts `os.rmdir(temp_dir)` (gracefully handles non-empty dirs)

3. **Exception Handling Philosophy**
   - **Total failure:** Raise `RuntimeError` with diagnostic message (e.g., "all N segments failed")
   - **Partial failure:** Log `warning` with count but return partial results
   - **Write failures:** Always propagate exceptions (never swallow)
   - **Cleanup:** Always runs in `finally` block regardless of outcome

4. **Logging Configuration**
   - **Entry point (main.py):** Calls `logging.basicConfig()` once at module level
   - **Library code (helper.py):** Only imports and uses `logging`; does NOT configure
   - Pattern ensures single configuration point, prevents conflicts

5. **Cross-Platform File Opening**
   - Used `sys.platform` detection over `webbrowser.open()`
   - **Rationale:** More control; webbrowser may launch browser instead of native text editor
   - Windows: `os.startfile()`, macOS: `subprocess.run(["open", ...])`, Linux: `subprocess.run(["xdg-open", ...])`

6. **Type Hints**
   - Added full type annotations to all 7 functions in helper.py
   - Used `Optional[AudioSegment]` for `get_audio_channel()` return (can be None on error)
   - Preserved function signatures exactly to avoid breaking Hudson's tests

**Files Modified:**
- `main.py`: Env var loading, logging, finally block, cross-platform opener
- `helper.py`: `MINUTE_TO_MILLI` rename, tempfile usage, exception propagation, logging, type hints, `recognize_azure` fix

**Verification:**
- ✅ No `SECOND_TO_MILLI` references in code
- ✅ All `print()` replaced with `logging`
- ✅ All functions type-hinted
- ✅ No `logging.basicConfig()` in helper.py
- ✅ Credentials loaded from env vars with startup validation
- ✅ Cleanup in `finally` block
- ✅ Exceptions propagated correctly

**Documentation:**
- Created `.squad/decisions/inbox/ripley-code-fixes.md` with complete implementation summary
- Includes API discoveries, design rationale, testing notes for Hudson

**Status:** Implementation complete; ready for Dallas review and Hudson test coverage.

### 2026-04-13 — OpenAI-Whisper Backend + Gradio GUI (Phase 1) Implemented

Completed implementation of Dallas's approved architecture for multi-backend support and GUI (Phase 1).

**Key Implementation Decisions:**

1. **`transcribe_pipeline()` Signature**
   - Created shared pipeline function with `progress_callback: Optional[Any]` parameter
   - Signature: `(input_source, backend, model_size, device, azure_speech_key, azure_ai_location, output_dir, progress_callback) -> Tuple[str, str]`
   - Returns `(full_transcript_text, output_file_path)` for both CLI and GUI consumption
   - CLI passes `None` for progress_callback; GUI passes Gradio `gr.Progress` updater
   - Uses 5-step progress model: validate → resolve source → extract audio → transcribe → write output
   - Cleanup handled in `finally` block: temp audio files + YouTube temp dirs

2. **OpenAI-Whisper API Differences**
   - `openai-whisper` uses `whisper.load_model()` vs faster-whisper's `WhisperModel()`
   - Returns dict with `result["segments"]` vs faster-whisper's iterator
   - PyTorch device detection: `torch.cuda.is_available()` vs ctranslate2's `get_supported_compute_types()`
   - Error message includes PyTorch CUDA wheel installation instructions
   - Documented 2-3x slower than faster-whisper due to PyTorch overhead

3. **Gradio 5.x Patterns Used**
   - `gr.Blocks()` with `gr.Tabs()` for Phase 1 (Transcribe tab only; Q&A tab in Phase 2)
   - Dynamic visibility: `backend_radio.change()` handler updates model/device/Azure credential visibility
   - `gr.Progress(track_tqdm=False)` for manual progress updates via callback
   - File upload with `file_types` filter for common video/audio formats
   - `gr.Textbox(type="password")` for Azure key input
   - `gr.File()` output for download link
   - `create_app()` returns `gr.Blocks` demo; `launch()` calls `demo.launch(server_port=7860)`

4. **pyproject.toml Extras Structure**
   - `[whisper]` — faster-whisper + CUDA 12.x shims (existing)
   - `[whisper-pytorch]` — openai-whisper for CUDA 13.x users
   - `[gui]` — gradio>=5.0.0
   - `[all]` — installs all three extras
   - `[project.scripts]` — `media-transcriber` (CLI) and `media-transcriber-gui` (GUI) entry points
   - Updated `requires-python` to `>=3.10` (Gradio 5.x requirement; was `>=3.9`)

5. **CUDA 13.x Fallback Warning Update**
   - Updated `_cuda_fallback_warning()` with 4-step troubleshooting path
   - Step 1: Install `[whisper]` extra (provides CUDA 12.x shims automatically)
   - Step 2: Verify driver + toolkit version
   - Step 3: Check PATH for CUDA binaries
   - Step 4: **NEW:** If CUDA 13.x, switch to `--backend openai-whisper` (PyTorch tracks CUDA faster)
   - Mentions `[whisper-pytorch]` extra and links to ctranslate2 CUDA 13.x tracking issue

**Files Modified:**
- `helper.py`: Added `transcribe_with_openai_whisper()`, `transcribe_pipeline()`, updated `_cuda_fallback_warning()`
- `main.py`: Refactored to thin wrapper over `helper.transcribe_pipeline()`, added `openai-whisper` backend choice
- `pyproject.toml`: Added `[whisper-pytorch]`, `[gui]`, `[all]` extras; added `[project.scripts]`; updated `requires-python`
- `README.md`: Added GUI section, openai-whisper usage examples, CUDA 13.x troubleshooting sub-section
- `app.py`: **NEW FILE** — Gradio 5.x GUI with backend/model/device selectors, progress, file/URL input, copy + download

**Verification:**
- ✅ All tests pass (78 passed, 3 skipped)
- ✅ Syntax validation clean for helper.py, main.py, app.py
- ✅ Dependency resolution succeeds with new Python >=3.10 requirement
- ✅ Commit message follows convention with Co-authored-by trailer

**Documentation:**
- Created `.squad/decisions/inbox/ripley-phase1-impl.md` with implementation summary

**Status:** Phase 1 complete; committed to main branch (2581505).
