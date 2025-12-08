# 🗳️ AI Voting System for Blind Individuals (Prototype)

This project is a **voice-based voting system** designed to support **blind or visually impaired users** in casting votes securely using **speech input and audio prompts**. It's built with **Python + Streamlit**, uses **offline speech recognition (VOSK)** when possible, and falls back to **Google SpeechRecognition API**. Votes are stored securely in a local **SQLite database**.

> ⚠️ This is a **prototype** for demonstration purposes only. Do **not** use in production or real elections.


## 📦 Tech Stack

- Python 3.9+
- [Streamlit](https://streamlit.io/) – Web UI & backend
- [VOSK](https://alphacephei.com/vosk/) – Offline speech recognition (recommended)
- [SpeechRecognition](https://pypi.org/project/SpeechRecognition/) – Google Web Speech API (fallback)
- [pyttsx3](https://pypi.org/project/pyttsx3/) – Offline text-to-speech (TTS)
- SQLite – Local database


## 📁 Project Structure

ai_voting_system/
├── README.md
├── .gitignore
├── requirements.txt
├── streamlit_app.py # Main Streamlit app
├── voice_utils.py # ASR + TTS logic
├── db.py # Database schema and logic
├── models/ # Put VOSK models here (not versioned)
│ └── vosk-model-small-en-us-0.15/
└── assets/
└── sample_audio.wav # Optional demo audio file


## ⚙️ Installation

1. **Clone the repo**:
   ```bash
   git clone https://github.com/yourusername/ai-voting-system.git
   cd ai-voting-system

2. **Create a virtual environment (recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt

4. **(Optional) Download VOSK model:**:
    Download from: https://alphacephei.com/vosk/models
    Extract vosk-model-small-en-us-0.15 into:
    ```bash
    ai_voting_system/models/vosk-model-small-en-us-0.15/

5. **Run the app:**:
    ```bash
    streamlit run streamlit_app.py

6. Open the link in your terminal (usually http://localhost:8501).
    Use a good headset for best results.


## 🧪 Demo Voter IDs

Demo Voter ID: TEST1
Candidates:
    1: Alice
    2: Bob
    3: Charlie


## 🗣️ How It Works

1. Click Start Voice Voting.
2. App asks for voter ID via voice.
3. You speak your ID (e.g., "TEST1").
4. App announces candidates and asks you to say a number or name.
5. Confirms your choice, asks you to say "confirm".
6. Records the vote securely.


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