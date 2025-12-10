# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

This repository contains a prototype voice-driven voting system aimed at blind or visually impaired users. The current implementation is a Flask-based web app that delegates all microphone and text-to-speech work to a separate subprocess, with votes stored in a local SQLite database. The original README describes a Streamlit-based UI, but in this codebase the primary entrypoint is `web_voting_app.py` (Flask) plus its supporting subprocess and utilities.

Key technologies:
- Python 3.9+
- Flask (web UI + JSON APIs in `web_voting_app.py`)
- VOSK + PyAudio for offline ASR when available, falling back to Google SpeechRecognition
- pyttsx3 and Windows SAPI/other Windows TTS paths for text-to-speech
- SQLite for persistence (`votes.db`)

Refer to `README.md` for user-facing description, installation notes, and project limitations. The sections below focus on how to work productively in this codebase.

## Commands and workflows

### Environment setup

From the repo root:

```bash
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Run the web voting app (main workflow)

From the repo root, after installing dependencies:

```bash
# Direct entrypoint
python web_voting_app.py

# Or use the helper script (prints banner and runs the same app)
start_voting_system.bat
```

Behavior:
- Starts a Flask app on `http://127.0.0.1:5000`.
- Serves the main UI template `web_voting.html` (expected under a standard Flask `templates/` directory).
- When a voice voting session is started from the UI, the app spawns `voice_subprocess.py` in a separate Python process and writes its logs to `subprocess_<session_id>.log`.

### Test voter ID pattern logic ("single test" example)

The repository includes a focused test script for the voter ID recognition pattern:

```bash
python test_voter_id.py
```

This prints which spoken variants are treated as valid voter IDs and should be used as a reference when adjusting the regex in `voice_subprocess.py`.

### Test Windows TTS in isolation

To verify Windows TTS behavior from a subprocess context:

```bash
python windows_tts.py
```

This exercises the `speak_subprocess_safe` helper, trying multiple Windows TTS mechanisms.

### Reset local database state

Votes are stored in `votes.db` in the project root. To wipe all votes and demo data during development, stop the app and delete this file; it will be recreated with demo data by `init_db()` the next time `web_voting_app.py` runs.

## High-level architecture

### Web layer: `web_voting_app.py`

Responsibilities:
- Creates the Flask application and defines all HTTP routes.
- Initializes the SQLite database on startup via `init_db()` from `db.py`.
- Maintains an in-memory `voting_sessions` dict keyed by `session_id`, each entry holding the subprocess handle, current status/step/message, and final result (if any).
- Renders the main voting page (`/`) via the `web_voting.html` template.
- Exposes JSON APIs used by the frontend:
  - `GET /api/candidates` – returns the candidate list from `db.get_candidates()`.
  - `POST /api/start-voice-voting` – allocates a new `session_id`, spawns `voice_subprocess.py <session_id>` via `subprocess.Popen`, and initializes session state and a log file `subprocess_<session_id>.log`.
  - `GET /api/voting-status/<session_id>` – polls for progress. It reads `status_<session_id>.json` if present (written by the voice subprocess) to update status, and inspects the subprocess return code to know whether the session is still running or complete.
  - `GET /api/results` – fetches aggregated vote counts from `db.get_votes()`.
  - `GET /api/reset-session/<session_id>` – terminates the associated subprocess (if still running), cleans up the session entry and status file.

This file is the main integration point between HTTP/UI concerns and the voice-processing subsystem.

### Voice subprocess: `voice_subprocess.py`

This module is designed to run as a separate Python process, isolating audio libraries from the web framework and simplifying cleanup.

Key responsibilities:
- Orchestrates the three-step voice voting flow for a single `session_id`:
  1. **Voter ID capture** – prompts the user via TTS, listens for a spoken ID, and validates it using a permissive regex that matches several "first one" variants (e.g., "firstone", "first van", etc.).
  2. **Candidate selection** – reads out all candidates from `db.get_candidates()`, asks the user to speak a candidate number, and parses the first integer found in the transcription.
  3. **Confirmation** – asks the user to say "confirm" to cast the vote or any other phrase (including explicit "cancel") to abort.
- Uses `windows_tts.speak_subprocess_safe` for all audio prompts, since it is optimized for use in subprocesses on Windows.
- Uses `voice_utils.listen()` for speech recognition, preferring VOSK with a local model, and falling back to the Google SpeechRecognition API if needed.
- Writes incremental progress updates and the final outcome to `status_<session_id>.json` via `send_status()` and `send_final_result()`. The Flask app polls these files.
- Records successful votes in the database via `db.record_vote(valid_voter_id, candidate_id)`.
- Provides verbose logging through `console_utils.safe_print` so that both normal output and error conditions are traceable in the subprocess log files.

If you modify the voting flow (e.g., new steps or different validation), ensure the structure of the status JSON remains compatible with the polling logic in `web_voting_app.py` or update both sides together.

### Audio utilities and speech recognition: `voice_utils.py`

`voice_utils.py` centralizes microphone access, audio cleanup, and text-to-speech behavior when running in a normal (non-subprocess) process.

Major concerns:
- **Text-to-speech (pyttsx3)**
  - Global `engine` instance guarded by `_engine_lock` to avoid re-entrant `runAndWait()` errors.
  - `speak()` and `speak_and_wait()` log their activity, handle known runtime errors (e.g., "run loop already started") by waiting for the engine to be free and retrying once, and then enforce small sleep delays to avoid audio device conflicts.
  - Atexit and signal handlers (`_cleanup_all`, `_shutdown_tts`, `_signal_handler`, `_setup_signal_handlers`) attempt to ensure the pyttsx3 engine and any PyAudio resources are cleanly torn down on exit or Ctrl+C.

- **Offline ASR with VOSK**
  - `VOSK_AVAILABLE` is determined by optional imports of `vosk` and `pyaudio`.
  - `MODEL_DIR` points to `models/vosk-model-small-en-us-0.15` under the repo root; `recognize_from_vosk()` returns `None` if either the library or model directory is missing.
  - Handles sample-rate fallbacks (e.g., from 16 kHz to 44.1 kHz) and logs partial and final transcripts during recording.

- **Online ASR with Google SpeechRecognition**
  - `recognize_with_google()` uses `speech_recognition` with configurable timeout, `device_index`, and energy threshold, performing multiple short listening attempts within the overall timeout.
  - Returns a lowercase transcription string on success or `None` on failure/service errors.

- **Unified listening interface**
  - `listen()` orchestrates the above: it tries VOSK first if available and the model exists, otherwise falls back to the Google recognizer, logging which path was taken and the resulting text.

- **Diagnostics helpers**
  - `test_microphone()` wraps `recognize_with_google()` for a quick capture.
  - `monitor_audio_levels()` uses PyAudio + NumPy to show a live ASCII/Unicode audio level bar for calibration.
  - `list_microphones()` enumerates available microphone names.

These utilities are used heavily by `voice_subprocess.py` and are the main place to adjust microphone behavior, thresholds, or error handling.

### Windows-specific TTS utilities: `windows_tts.py`

This module provides several Windows-only TTS backends and a unified safe wrapper:
- `speak_windows_sapi(text)` – uses PowerShell and `System.Speech.Synthesis.SpeechSynthesizer`.
- `speak_windows_command(text)` – writes a temporary VBScript that invokes SAPI via `cscript`.
- `speak_windows_narrator(text)` – invokes the Windows Narrator with a temporary text file.
- `speak_subprocess_safe(text)` – tries the above methods in order, logging which one succeeded or that all failed.

`voice_subprocess.py` uses `speak_subprocess_safe()` to provide robust audio output from a subprocess on Windows, where direct pyttsx3 use can be unreliable.

### Persistence layer: `db.py`

`db.py` encapsulates all SQLite access and schema management:
- Uses `votes.db` in the project root (`DB_PATH`).
- `init_db()` creates three tables if they do not exist: `voters`, `candidates`, `votes`, and seeds demo data for one voter and three candidates.
- `get_candidates()` returns `(id, name)` rows for use in both the web app and voice subprocess.
- `record_vote(voter_token, candidate_id)` inserts a new row into `votes` with an auto-incrementing ID and timestamp.
- `get_votes()` returns `(candidate_id, count)` rows for display in result views.

All database interactions are simple, short-lived connections opened per function call.

### Console utilities: `console_utils.py`

Provides Windows-safe printing helpers:
- `safe_print(text)` prints strings containing emojis or extended Unicode, falling back to ASCII replacements when the console encoding cannot represent certain characters.
- `enable_utf8_console()` attempts to switch Windows consoles to UTF-8 code page via `chcp 65001`.

All long-running modules use `safe_print` to ensure logs remain readable on Windows.

### Test script: `test_voter_id.py`

This script exercises the same voter ID regex as `voice_subprocess.py` using a small set of representative phrases. It is useful when adjusting spoken ID patterns; keep the regex in `voice_subprocess.py` and the expectations in this script in sync.

### Models directory

The `models/` directory is expected to contain VOSK models. The default path used in code is:

- `models/vosk-model-small-en-us-0.15/`

Ensure this directory exists and contains a valid VOSK model for offline recognition to work; otherwise, `voice_utils.listen()` will fall back to the Google recognizer.
