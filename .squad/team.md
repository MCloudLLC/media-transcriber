# Squad Team

> media-transcriber

## Coordinator

| Name | Role | Notes |
|------|------|-------|
| Squad | Coordinator | Routes work, enforces handoffs and reviewer gates. |

## Members

| Name | Role | Charter | Status |
|------|------|---------|--------|
| Dallas | Lead | .squad/agents/dallas/charter.md | 🟢 Active |
| Ripley | Backend Dev | .squad/agents/ripley/charter.md | 🟢 Active |
| Hudson | Tester | .squad/agents/hudson/charter.md | 🟢 Active |
| Scribe | Session Logger | .squad/agents/scribe/charter.md | 🟢 Active |
| Ralph | Work Monitor | — | 🔄 Monitor |

## Project Context

- **Project:** media-transcriber
- **Stack:** Python 3.8+, Azure Speech API (azure-cognitiveservices-speech), pydub, ffmpeg
- **What it does:** Extracts audio from video files → splits into 1-min segments → transcribes with Azure Speech-to-Text → saves to `.txt`
- **Key files:** `main.py` (entry point), `helper.py` (audio utilities)
- **User:** Copilot
- **Created:** 2026-04-13
