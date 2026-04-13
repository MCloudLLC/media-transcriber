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
