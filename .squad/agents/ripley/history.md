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
