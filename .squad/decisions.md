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

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
