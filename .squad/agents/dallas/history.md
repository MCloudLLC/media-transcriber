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
