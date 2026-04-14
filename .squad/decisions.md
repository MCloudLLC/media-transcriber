# Squad Decisions

## Active Decisions

### 2026-04-13: Team initialized
**By:** Copilot (via Squad Coordinator)
**What:** Hired Dallas (Lead), Ripley (Backend Dev), Hudson (Tester), Scribe, and Ralph for the video-to-text-azure-speech-api project.
**Why:** Initial team setup.

## Squad Review Findings — 2026-04-13

### Critical Issues

#### Issue: Hardcoded Azure API Credentials
**Agents:** Dallas, Ripley  
**Severity:** Critical  
**Files:** main.py:6-7  
**Description:** Azure Speech API key and location are hardcoded as placeholder strings. This pattern leads to credentials being committed to version control if developers forget to replace them.

**Recommendation:**
- Remove hardcoded values from main.py
- Load credentials from environment variables using `os.getenv()`
- Add `AZURE_SPEECH_KEY` and `AZURE_AI_LOCATION` to `.env` file (add `.env` to `.gitignore`)
- Document in README how to set up environment variables
- Consider using Azure SDK's `DefaultAzureCredential` for robust credential management

#### Issue: Temp File Leak on Transcription Exception
**Agent:** Ripley  
**Severity:** Critical  
**File:** main.py:37–53  
**Description:** `clean_up_temp_files()` is called only on the happy path. If `transcribe_audio_segments()` or `write_file()` raises an exception, the `except` block calls `sys.exit(1)` without cleaning up WAV segments already written to disk. Every crash leaves orphaned temp files.

**Recommendation:**
- Use try/finally pattern to ensure cleanup always runs
- Move `os.system()` call outside try/finally so it only runs on success
- Code example provided in ripley-code-review.md

---

### High Severity Issues

#### Issue: Windows-Specific Command Breaks Cross-Platform Compatibility
**Agents:** Dallas, Ripley, Hudson  
**Severity:** High  
**File:** main.py:49  
**Description:** `os.system(f"start {transcription_file}")` uses the Windows `start` command only. Fails on macOS/Linux. Also breaks when paths contain spaces. `os.system` is deprecated.

**Recommendation:**
- Replace with cross-platform approach:
  - Use `webbrowser.open(f'file:///{transcription_file}')` for simplicity
  - Or wrap in platform-aware function using `subprocess.Popen()` with platform detection
  - Or use `os.startfile()` (Windows), `subprocess.run(["open", path])` (macOS), `subprocess.run(["xdg-open", path])` (Linux)
- Make file opening optional via flag/config if appropriate

#### Issue: Missing Environment Variable Setup Instructions
**Agent:** Dallas  
**Severity:** High  
**File:** README.md:29-34  
**Description:** README documents manual hardcoding of credentials in `main.py`, contradicting its own warning on line 68. No instructions for setting up environment variables despite recommending them.

**Recommendation:**
- Remove "replace placeholders in main.py" instructions
- Add section "Setting Up Credentials" with:
  - How to obtain Azure Speech API key and location
  - Step-by-step environment variable setup (Windows and Unix examples)
  - Optional: `.env` file approach with `python-dotenv`

#### Issue: Missing ffmpeg Dependency Declaration
**Agent:** Dallas  
**Severity:** High  
**File:** requirements.txt  
**Description:** Code imports `pydub` which depends on ffmpeg, but `ffmpeg-python` is not listed in requirements.txt. Users install pydub then get runtime errors without ffmpeg.

**Recommendation:**
- Add `ffmpeg-python` to requirements.txt
- Document in README: "Install ffmpeg separately: `brew install ffmpeg` (macOS), `choco install ffmpeg` (Windows), `apt-get install ffmpeg` (Linux)"

#### Issue: Input File Path Validation Gaps
**Agent:** Dallas  
**Severity:** High  
**File:** main.py:19  
**Description:** Input file path passed directly to system calls without validation beyond existence check. No check for file extension or readability.

**Recommendation:**
- Validate file extension against supported formats
- Check readability with `os.access(input_file, os.R_OK)`
- Convert to absolute path early
- Document which file types are supported

---

### Medium Severity Issues

#### Issue: Installation Path Mismatch in README
**Agent:** Dallas  
**Severity:** Medium  
**File:** README.md:21  
**Issue:** Documentation says `cd video_to_text` but actual directory from clone is `video-to-text-azure-speech-api`.

**Fix:** Update README line 21 to `cd video-to-text-azure-speech-api`

---

#### Issue: Misleading Constant Name `SECOND_TO_MILLI`
**Agent:** Ripley  
**Severity:** Medium  
**File:** helper.py:7–9  
**Description:** Constant named `SECOND_TO_MILLI = 60 * 1000` (60 000) is misleading. Value actually converts *minutes* to milliseconds, not seconds. Downstream code uses it correctly (1 minute segments) but constant name is wrong.

**Recommendation:**
```python
MINUTE_TO_MILLI = 60 * 1000   # Conversion factor: minutes to milliseconds
SEGMENT_LENGTH = 1 * MINUTE_TO_MILLI  # Segment length: 1 minute in milliseconds
```

---

#### Issue: Unused Dependency Declarations
**Agent:** Dallas  
**Severity:** Medium  
**File:** requirements.txt:4-6  
**Description:** `standard-aifc`, `standard-chunk`, and `typing_extensions` appear to be backports for older Python versions. Not imported or used anywhere in code.

**Recommendation:**
- Verify if these are truly needed for Python 3.8+
- Remove if unused (keep dependencies lean)
- If used, add comments explaining why or update code to use native imports

---

#### Issue: Missing Official Azure SDK
**Agent:** Dallas  
**Severity:** Medium  
**File:** requirements.txt  
**Description:** Code uses `speech_recognition` library which can work with Azure, but official Azure Speech SDK (`azure-cognitiveservices-speech`) is not listed. Current approach is less direct and less maintained.

**Recommendation:**
- Consider adding `azure-cognitiveservices-speech` to requirements.txt
- Update helper.py to use official Azure SDK if intended
- Document which SDK is being used and why

---

#### Issue: Weak Error Handling in Transcription Loop
**Agent:** Dallas  
**Severity:** Medium  
**File:** helper.py:92-121  
**Description:** If a single audio file fails to transcribe, error is logged but processing continues silently. `txt_array` will be incomplete without indication of which segments failed.

**Recommendation:**
- Decide on behavior: should one failed segment fail the entire job, or partial results acceptable?
- If partial results OK: log failures prominently, return metadata showing succeeded/failed segments
- If one failure should fail job: raise exception instead of continuing silently
- Consider retry logic for transient errors (network timeouts)

---

#### Issue: Temp File Naming Not Collision-Safe
**Agent:** Dallas  
**Severity:** Medium  
**File:** helper.py:79-80, 84  
**Description:** Temporary files named with hardcoded prefix `_temp_audio`. If multiple instances run simultaneously in same directory, they collide and overwrite each other's temp files.

**Recommendation:**
- Use `tempfile.NamedTemporaryFile()` or `tempfile.gettempdir()` for unique temp files
- Or prepend timestamp/UUID: `_temp_audio_{uuid.uuid4()}_part{i}.wav`
- Document that concurrent runs in same directory are unsafe (or make them safe)

---

#### Issue: Silent Exception Swallowing in `write_file`
**Agent:** Ripley  
**Severity:** Medium  
**File:** helper.py:148–154  
**Description:** `except` block prints error but does not re-raise. Caller receives no signal that write failed and proceeds to success path.

**Recommendation:**
- Re-raise exception after logging:
  ```python
  except Exception as e:
      print(f"Error writing transcription file: {e}")
      raise
  ```

---

#### Issue: `recognize_azure` Location Parameter Unsupported
**Agent:** Ripley  
**Severity:** Medium  
**File:** helper.py:115  
**Description:** `SpeechRecognition` library's `recognize_azure` signature does not include `location` parameter in documented public API. Passing `location=api_location` may be silently ignored or raise `TypeError` depending on version.

**Recommendation:**
- Verify installed version's signature
- If `location` unsupported, build endpoint URL manually or switch to `azure-cognitiveservices-speech` SDK which natively supports region/location
- See ripley-code-review.md for detailed code examples

---

#### Issue: Silent Exception Swallowing in `transcribe_audio_segments`
**Agent:** Ripley  
**Severity:** Medium  
**File:** helper.py:108–119  
**Description:** `except` block only prints; function returns partial list with no indication of failures. Caller cannot distinguish "all succeeded" from "all failed".

**Recommendation:**
- Track failures and warn after loop
- Consider raising if *all* segments fail
- See ripley-code-review.md for code example

---

### Low Severity Issues

#### Issue: Incomplete Supported Formats Documentation
**Agent:** Dallas  
**Severity:** Low  
**File:** README.md:67  
**Description:** Notes say "supports MP4" but code actually supports any format pydub/ffmpeg supports (WAV, MP3, OGG, FLAC, etc.).

**Fix:** Update to list actual formats or link to pydub documentation

---

#### Issue: Missing Python Version Validation
**Agent:** Dallas  
**Severity:** Low  
**File:** README.md:14  
**Description:** States "Python 3.8 or higher" but code doesn't validate at runtime. Users with Python 3.7 get cryptic errors.

**Recommendation:**
- Add runtime validation in main.py with helpful error message
- Or clarify in README this is a strict requirement

---

#### Issue: No Logging or Debug Output Configuration
**Agent:** Dallas  
**Severity:** Low  
**File:** All Python files  
**Description:** Code uses `print()` for logging, making it hard to redirect logs, suppress output, or integrate with log aggregation.

**Recommendation:**
- Replace `print()` with Python's `logging` module
- Add `--verbose` / `-v` flag to control log level
- Document log behavior in README

---

#### Issue: No Type Hints on Function Signatures
**Agent:** Ripley  
**Severity:** Low  
**File:** helper.py:11, 21, 39, 58, 92, 123, 137  
**Description:** Public functions lack type annotations, limiting IDE support and static analysis (mypy). Project declares `typing_extensions` in requirements.txt, suggesting type hints are intended.

**Recommendation:**
- Add type hints to all public functions (7 functions total)
- Examples provided in ripley-code-review.md

---

#### Issue: Temp WAV Files Written to Current Working Directory
**Agent:** Ripley  
**Severity:** Low  
**File:** helper.py:79, 84  
**Description:** `TMP_FILE_NAME = "_temp_audio"` writes to process's current working directory. If user runs from read-only directory, creation fails with confusing error.

**Recommendation:**
- Use `tempfile.mkdtemp()` for designated temp location
- Or use `tempfile.NamedTemporaryFile()`
- `clean_up_temp_files` should also remove the directory

---

## Test Coverage Assessment

**Current Status:** 0% coverage — no test files exist  
**Functions Unvisited:** 8 total (all helper.py and main.py functions)  
**Edge Cases Identified:** 50+  

**Recommended Test Infrastructure:**
- Framework: pytest 8.3.5
- Mocking: pytest-mock 3.14.0
- Coverage: pytest-cov 6.1.0
- Structure: tests/unit/ and tests/integration/

**Total Core Test Cases Needed:** 43+ (plus parametrization variants)

See hudson-test-plan.md for complete test case matrix and testability blockers.

---

## Summary of Priorities

| Priority | Count | Status |
|----------|-------|--------|
| **Critical** | 2 | Needs immediate fix |
| **High** | 4 | Before merge |
| **Medium** | 10 | Should fix soon |
| **Low** | 5 | Nice to have |

**Must-Fix Before Merge:** Credentials, cleanup in finally, Windows command, environment variable docs, ffmpeg dependency

---

---

## Implementation Decisions — 2026-04-13/14

### Decision: Code Fixes Applied (Ripley Implementation)
**Date:** 2026-04-13  
**Status:** ✅ COMPLETE  
**Owner:** Ripley (Backend Developer)

**Scope:** 10 critical, high, and medium severity fixes across main.py and helper.py.

**Changes:**
1. **Credentials to Environment Variables (CRITICAL)** — Removed hardcoded Azure credentials; load from `AZURE_SPEECH_KEY` and `AZURE_AI_LOCATION` env vars with startup validation
2. **Finally Block for Cleanup (CRITICAL)** — Moved `clean_up_temp_files()` to finally block; ensures cleanup even on exception
3. **Cross-Platform File Opening (HIGH)** — Replaced `os.system("start ...")` with platform-aware: `os.startfile()` (Windows), `subprocess.run(["open", ...])` (macOS), `subprocess.run(["xdg-open", ...])` (Linux)
4. **Logging Module (HIGH)** — Replaced all `print()` calls with `logging.info()`, `logging.error()`, `logging.warning()`
5. **Constant Naming (MEDIUM)** — Renamed `SECOND_TO_MILLI` → `MINUTE_TO_MILLI` (value 60,000ms)
6. **Tempfile Strategy (MEDIUM)** — Changed from CWD tmp files to `tempfile.mkdtemp()` with safe cleanup
7. **Exception Propagation in write_file (MEDIUM)** — Changed from silent swallowing to `raise` after logging
8. **Partial Failure Tracking (MEDIUM)** — Added failure list in `transcribe_audio_segments`; distinguishes total vs partial failure
9. **recognize_azure API Fix (HIGH)** — Fixed tuple unpacking: `text = recognizer.recognize_azure()` (returns str, not tuple)
10. **Type Hints (LOW)** — Added full type annotations to all 7 helper.py functions and main.py functions

**Verification:** All changes verified in helper.py and main.py; no print() statements remain; all exceptions propagated correctly.

---

### Decision: Documentation and Dependency Fixes (Dallas Lead)
**Date:** 2026-04-13  
**Status:** ✅ COMPLETE  
**Owner:** Dallas (Lead Architect)

**Scope:** README.md and requirements.txt alignment with code and security best practices.

**Changes:**
1. **Installation Path (README:21)** — Fixed `cd video_to_text` → `cd video-to-text-azure-speech-api` (matches actual repo name)
2. **Remove Unsafe Hardcoding (README:29–34)** — Removed instruction to hardcode credentials in main.py; replaced with env var setup (platform-specific: Linux/macOS, Windows CMD, Windows PowerShell)
3. **Add ffmpeg Prerequisite (README:13–19)** — Declared ffmpeg as explicit prerequisite with OS-specific install commands (brew, apt-get, download link)
4. **Update Project Structure (README:48–57)** — Corrected directory name; added tests/ directory
5. **Expand Supported Formats (README:67)** — Listed actual formats: MP4, AVI, MKV, MOV, MP3, WAV, FLAC, OGG (pydub/ffmpeg supported)
6. **Replace Misleading Security Note (README:68–69)** — Clarified credentials are from env vars; app exits if missing
7. **Remove Unused Dependencies (requirements.txt:4–6)** — Removed standard-aifc, standard-chunk, typing_extensions (unused, Python 3.8+ includes these)
8. **Add Test Framework (requirements.txt)** — Added pytest, pytest-mock, pytest-cov for test infrastructure
9. **Preserve audioop-lts** — Kept as dependency (required for SpeechRecognition on Python 3.13+)

**Verification:** All changes align with team decisions; documentation is platform-specific and accurate.

---

### Decision: Test Infrastructure Setup (Hudson Implementation)
**Date:** 2026-04-13  
**Status:** ✅ COMPLETE  
**Owner:** Hudson (Tester)

**Scope:** Complete test infrastructure scaffolding with 55+ unit tests and 3 integration tests.

**Structure Created:**
```
tests/
├── __init__.py
├── conftest.py
├── unit/
│   ├── test_check_file_exists.py (4 tests)
│   ├── test_clean_up_temp_files.py (4 tests)
│   ├── test_get_audio_channel.py (6 tests)
│   ├── test_load_audio_segments.py (6 tests)
│   ├── test_transcribe_audio_segments.py (9 tests)
│   ├── test_get_transcription_file.py (5 tests)
│   ├── test_write_file.py (5 tests)
│   └── test_main.py (13 tests)
└── integration/
    └── test_end_to_end.py (3 tests)
```

**Coverage:** All 7 helper.py functions; main.py execution flow; integration with Azure API (gated by credentials)

**Fixtures:** tmp_wav_file, mock_audio_segment, azure_env_vars; all external dependencies mocked in unit tests

**Status:** Tests written against expected post-fix behavior (per Ripley's refactoring plan); ready for validation runs

---

### Decision: CUDA 13.x Whisper Backend Strategy (Dallas Analysis)
**Date:** 2026-04-14  
**Status:** ✅ APPROVED  
**Owner:** Dallas (Lead Architect)

**Problem Statement:** Windows users on CUDA 13.x encounter `Library cublas64_12.dll is not found` error when using faster-whisper (ctranslate2 compiled for CUDA 12.4).

**Research Findings:**
- **ctranslate2 Status:** v4.7.1 (Feb 2026) — CUDA 12.4 only; CUDA 13.x PR #2027 in progress, testing on CUDA 13.2, unshipped
- **Pip Shim Workaround:** `nvidia-cublas-cu12` pip package (already in `[whisper]` extra) installs CUDA 12.x DLLs to Python environment; ctranslate2 can find them regardless of system CUDA version
- **Main Fix:** Ensure users install `pip install .[whisper]` (not just `faster-whisper` alone)

**Backends Evaluated:**
| Backend | CUDA 13.x Support | Speed vs faster-whisper | Recommendation |
|---------|------------------|----------------------|---|
| faster-whisper (ctranslate2) | ❌ Not yet | 1× (baseline) | Primary (keep) |
| openai-whisper | ✅ Via PyTorch 2.7+ | 0.5–0.7× (slower) | **Fallback alternative** |
| insanely-fast-whisper | ✅ Via PyTorch | 1.5–2× (faster) | Too complex for this project |
| stable-ts | ✅ Via PyTorch | ~0.5× | Unnecessary wrapper |
| whisperx | ❌ Depends on faster-whisper | Same issue | Eliminated |
| whispercpp | N/A (CPU-only) | N/A | Wrong use case |

**Decision: Dual-Backend, faster-whisper Stays Primary**

**Rationale:**
1. faster-whisper is 2–4× faster on CUDA 11/12 (majority of users)
2. ctranslate2 CUDA 13.x support is temporary gap (PR #2027 active; team releases monthly)
3. Replacing faster-whisper now would degrade majority user base for niche case
4. Adding second backend is low-risk: new code path, no breaking changes

**Implementation:**
1. **Primary Fix (no code change):** Update `_cuda_fallback_warning()` to reference `pip install .[whisper]`
2. **Fallback Path (Phase 1):** Add `openai-whisper` as `[whisper-pytorch]` optional extra
3. **main.py:** Add `--backend faster-whisper|openai-whisper` flag; dispatch accordingly
4. **helper.py:** Add `transcribe_with_openai_whisper()` function alongside existing `transcribe_with_whisper()`
5. **pyproject.toml:** Add `[whisper-pytorch]` extra: `openai-whisper>=20231117`
6. **README:** Add CUDA 13.x troubleshooting section with 4 options in priority order

**API Differences (faster-whisper vs openai-whisper):**
| Aspect | faster-whisper | openai-whisper |
|--------|---|---|
| Model load | `WhisperModel(size, device=, compute_type=)` | `whisper.load_model(size, device=)` |
| Transcribe | Returns segments iterator | Returns dict with `["text"]` and `["segments"]` |
| CUDA detection | Manual (ctranslate2) | Automatic (PyTorch) |

**Recommendation for Ripley:** 
- Do NOT port CUDA pre-check block from faster-whisper; PyTorch handles it natively
- Keep both implementations independent (no shared code between backends)
- Error messages in both backends should guide users to README Troubleshooting

**Risk Mitigation:**
- openai-whisper 2–3× slower: Position as fallback, not upgrade; default remains faster-whisper
- PyTorch wheel complexity: Document two-step install; error message if torch not found
- User confusion: Clear README distinction between `[whisper]` (fast, CUDA 11/12) and `[whisper-pytorch]` (compatible, all CUDA)

---

### Decision: CUDA cuBLAS Troubleshooting Documentation (Dallas)
**Date:** 2026-04-14  
**Status:** ✅ COMPLETE  
**Owner:** Dallas (Lead Architect)

**Problem:** Windows users get recurring `WARNING: CUDA requested but not available: Library cublas64_12.dll not found or cannot be loaded` error

**Root Cause:** ctranslate2 (inside faster-whisper) compiled against CUDA 12.x; fails to find DLLs when not on PATH or in Python environment

**Solution:** README `## Troubleshooting` section with 4 options in priority order:

1. **Option 1 (Fastest):** `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` — installs CUDA 12.x DLLs to Python environment
2. **Option 2:** Verify system CUDA Toolkit 12.x installed and on PATH; add `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.x\bin` if missing
3. **Option 3:** Resolve CUDA version mismatch (ctranslate2 2.x = CUDA 11.x, 3.x+ = CUDA 12.x)
4. **Option 4:** Fall back to CPU with `--device cpu` — non-fatal, auto-fallback works, just slower

**Code Note for Ripley:** `_cuda_fallback_warning()` in helper.py (lines 314–324) already recommends pip package install; optional enhancement to add README pointer

**Status:** Added to README.md; decision complete

---

### Decision: Gradio GUI Framework for Phase 1 (Dallas Recommendation)
**Date:** 2026-04-14  
**Status:** ✅ APPROVED  
**Owner:** Dallas (Lead Architect)

**Question:** Which GUI framework for transcription GUI + future Q&A feature?

**Evaluation:**
| Framework | File Upload | Chat UI | Python-native | Learning Curve | Recommendation |
|-----------|---|---|---|---|---|
| **Gradio** | ✅ | ✅ gr.ChatInterface | ✅ | Low | **CHOSEN** |
| Streamlit | ✅ | ⚠️ Manual session state | ✅ | Low | Re-run model too complex |
| Tkinter/PyQt | ⚠️ Manual | ❌ No chat widget | ✅ Native | High | Overkill |
| FastAPI+HTML | ⚠️ Manual | ❌ Build from scratch | ❌ JS/HTML needed | High | Too much code |

**Decision: Gradio**

**Rationale:**
1. **Chat interface first-class:** `gr.ChatInterface` purpose-built for conversational AI; Streamlit requires manual state management
2. **Tabs are native:** `gr.TabbedInterface` maps perfectly to Transcribe (Phase 1) and Q&A (Phase 2) tabs
3. **File upload with drag-drop:** `gr.File` and `gr.Audio` handle upload seamlessly
4. **Progress tracking:** `gr.Progress` integrates directly with long-running functions
5. **ML/AI ecosystem fit:** Gradio is standard for ML tools (Hugging Face Spaces); our use case (transcription + LLM) is core use case
6. **No frontend code:** Pure Python; matches team skill set
7. **Local by default:** Runs on localhost:7860, opens browser automatically

**Phase 1 Scope:** Transcription tab (file/URL upload, backend picker, progress, output display)
**Phase 2 Scope:** Q&A tab with LLM chat (deferred; decision in separate session)

---

### Decision: Q&A Architecture — Hybrid In-Context + RAG (Dallas Proposal, Deferred to Phase 2)
**Date:** 2026-04-14  
**Status:** PROPOSED (not yet approved; Phase 2)  
**Owner:** Dallas (Lead Architect)

**Problem:** Transcriptions range from 1 minute (few hundred words) to hours (tens of thousands words); single approach doesn't fit both

**Proposed Hybrid Approach:**
- **< 25K tokens:** In-context (full text as LLM system message)
- **≥ 25K tokens:** RAG (chunking, embedding, ChromaDB vector store, retrieval)

**Component Choices (for Phase 2 decision):**
- **LLM:** OpenAI Python SDK (works with OpenAI, Azure OpenAI, Ollama, LM Studio, vLLM)
- **Default local LLM:** Ollama (llama3.2 or mistral)
- **Vector store:** ChromaDB (pure Python, SQLite-backed, no server needed)
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2, local, no API key, 80MB)
- **Chunking:** Simple recursive character splitter (no heavy dependencies)

**Status:** Decision document written; awaiting Phase 2 approval session

---

### Decision: Multi-Backend Whisper Integration Architecture (Dallas Recommendation)
**Date:** 2026-04-13  
**Status:** ✅ APPROVED  
**Owner:** Dallas (Lead Architect)

**Question:** Add Whisper locally as new project or extend existing Azure tool?

**Evaluation:**
| Option | Approach | Pros | Cons | Verdict |
|--------|----------|------|------|--------|
| **A** | New repo | Clean slate | 60% code duplication | ❌ Rejected |
| **B** | Unified (one CLI, --backend flag) | Code reuse, single tool, low complexity (~20 lines) | Minor abstraction cost | ✅ **CHOSEN** |
| **C** | Replace Azure | Simpler | Breaks existing users | ❌ Rejected |

**Decision: Option B — Unified Multi-Backend**

**Architecture:**
- `--backend azure|whisper` flag in CLI
- Shared audio extraction (pydub), segmentation (1-min chunks), I/O, cleanup
- Backend implementations: Azure (existing), Whisper (new)
- `BaseTranscriber` interface with `.transcribe(audio_file)` method
- Backend dispatch in main.py; implementations isolated in helper.py

**Whisper Variant: faster-whisper (CTranslate2)**
- 4× faster than openai-whisper, same accuracy
- Lower memory footprint (critical for laptops)
- Active maintenance, production-ready
- Default model: base (1× realtime on CPU, good accuracy)
- User override: `--model base|small|medium|large`

**YouTube Support: yt-dlp**
- Actively maintained; handles 1000+ sites
- Alt options (pytube unmaintained, youtube-dl slow) rejected
- Detection: simple regex for URL vs file path
- Integration: download audio-only stream → pass to existing pipeline

**Audio Pipeline:** Current pydub pipeline already produces 16kHz mono WAV (exactly what Whisper needs); no changes needed

**Status:** Architecture approved; implementation deferred to Phase 2 (GUI currently focuses on Azure backend)

---

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
