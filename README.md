# 🗳️ AI Voting System for Blind Individuals (Prototype)

This project is a **voice-based voting system** designed to support **blind or visually impaired users** in casting votes securely using **speech input and audio prompts**. The current implementation is a **web-based Flask app** that uses a separate Python subprocess for microphone and text-to-speech work. When possible it uses **offline speech recognition (VOSK)** and otherwise falls back to the **Google SpeechRecognition API**. Votes are stored securely in a local **SQLite database**.

> ⚠️ This is a **prototype** for demonstration purposes only. Do **not** use in production or real elections.


## 📦 Tech Stack

- Python 3.9+
- Flask – Web UI & JSON APIs (`web_voting_app.py`)
- [VOSK](https://alphacephei.com/vosk/) – Offline speech recognition (recommended)
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) – Google Web Speech API (fallback)
- [pyttsx3](https://pypi.org/project/pyttsx3/) – Offline text-to-speech (TTS)
- Windows TTS (SAPI / Narrator / VBScript) – subprocess-safe TTS paths
- SQLite – Local database


## 📁 Project Structure

aio_voting_system/
├── README.md
├── requirements.txt
├── web_voting_app.py        # Flask web app + REST API
├── voice_subprocess.py      # Voice-driven voting flow (runs as separate process)
├── voice_utils.py           # ASR + TTS logic (VOSK + Google + pyttsx3)
├── windows_tts.py           # Windows-specific TTS helpers for subprocesses
├── console_utils.py         # Safe console logging with emoji fallbacks
├── db.py                    # Database schema and access helpers
├── models/
│   └── vosk-model-small-en-us-0.15/  # VOSK model directory (not versioned)
├── start_voting_system.bat  # Windows helper to start the web app
└── test_voter_id.py         # Small script to test voter ID pattern matching

> Note: The Flask app expects a `web_voting.html` template in a standard `templates/` folder (e.g., `templates/web_voting.html`).


## ⚙️ Installation

1. **Clone the repo**:
   ```bash
   git clone https://github.com/yourusername/ai-voting-system.git
   cd ai-voting-system
   ```

2. **Create a virtual environment (recommended)**:
   ```bash
   python -m venv venv
   # On Linux/macOS
   source venv/bin/activate
   # On Windows (PowerShell)
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   If you get an `ImportError: No module named 'flask'`, also install Flask:
   ```bash
   pip install flask
   ```

4. **(Optional) Download VOSK model:**
   - Download from: https://alphacephei.com/vosk/models
   - Extract `vosk-model-small-en-us-0.15` into:
   ```bash
   ai_voting_system/models/vosk-model-small-en-us-0.15/
   ```

5. **Run the app:**
   From the repo root:
   ```bash
   # Cross-platform entrypoint
   python web_voting_app.py

   # On Windows, you can also use the helper script
   start_voting_system.bat
   ```

6. Open your browser to `http://localhost:5000`.
   Use a good headset for best results.


## 🧪 Demo Voter IDs

The current prototype is tuned around a single demo voter conceptually called **"FIRST1"**, but the **spoken** voter ID is recognized as variations on **"first one"** (e.g., "first one", "firstone", "first van"). When prompted for your voter ID, say something that clearly sounds like “first one”.

Demo candidates (pre-seeded in the database):
- 1: BJP
- 2: CONGRESS
- 3: JDS

You vote by speaking the **number** of the candidate.


## 🗣️ How It Works

1. Open the web app in your browser and click **Start Voice Voting**.
2. The app asks for your voter ID via synthesized voice.
3. You speak your ID (e.g., something recognized as **"first one"**).
4. The subprocess announces the list of candidates and asks you to say a **number** (1, 2, or 3).
5. It repeats back what it heard, then asks you to say **"confirm"** to cast your vote or anything else (e.g., "cancel") to abort.
6. On a successful confirmation, it records the vote securely in the local SQLite database.


## 🛡️ Limitations & Next Steps

- Privacy: Voter IDs are stored. For real systems, use tokenization or blind signatures.
- Anti-Spoofing: Add liveness detection to prevent fake voice input.
- Languages: Add multi-language support (Hindi, regional languages).
- Deployment: Move backend off-device, use HTTPS/TLS, and secure authentication.
- Auditing: Must undergo legal, ethical, and security reviews before real-world use.


## 📈 Admin Features

- Right-side panel: Show Tally button
- Displays vote counts by candidate (real-time)


## 📄 License

This project is open for educational and non-commercial use only.


## 🤝 Contributions

Pull requests are welcome
- Suggest improvements
- Add support for new languages
- Integrate more secure vote verification
