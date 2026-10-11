# VoiceNotes — Patient Intake 
<img width="885" height="803" alt="notesapp" src="https://github.com/user-attachments/assets/329b3b52-936c-44da-9d3f-145583db3acf" />

A desktop app (PyQt6) for capturing structured patient intake records using voice, powered by local speech-to-text and an LLM for field extraction. Speak naturally into a field and the app transcribes, extracts the relevant value, and fills it in — or type it manually with a one-click override.

## Features

- **Per-field voice recording** — press the mic on any field to record just that value, with a live "listening" indicator.
- **Manual override** — every field can be unlocked and typed directly instead of using voice.
- **Structured intake form** organized into sections:
  - Demographics (name, age, gender)
  - Vitals (blood pressure, heart rate, temperature)
  - Clinical (chief complaint, allergies, diagnosis)
- **Voice commands** — say things like "next field," "clear field," or "confirm" while recording to control the form hands-free.
- **Vitals validation** — flags out-of-range values with an in-app warning banner before saving.
- **Multi-patient session management** — auto-incrementing patient IDs, a saved-patient list, and the ability to reload any patient back into the form.
- **Confirmation dialog** before committing a record, showing any validation warnings.
- **Audio upload** — process a pre-recorded audio file instead of recording live.
- **Notes & transcript tabs** — view the AI-generated structured notes alongside the raw transcript.
- **Dark / light theme toggle.**

## Requirements

- Python 3.9+
- pip
- A working microphone (for live recording)
- [Ollama](https://ollama.com/) installed and running, with the `mistral` model pulled:
  ```bash
  ollama pull mistral
  ```

Python dependencies (see `requirements.txt`):
- `PyQt6`, `PyQt6-Qt6`, `PyQt6_sip` — desktop UI
- `openai-whisper` — speech-to-text transcription
- `ollama` — LLM client for field extraction from transcripts
- `sounddevice` — audio recording
- `numpy`, `scipy` — audio processing

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/dvyuh/notesApp.git
   cd notesApp
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   ```
   - macOS / Linux:
     ```bash
     source venv/bin/activate
     ```
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Make sure Ollama is running locally with the `mistral` model available.

## Usage

Run the app:

```bash
python main.py
```

1. Select a field and press the mic button to record your input for that field, or press ** Override** to type it manually.
2. Say "next field," "clear field," or "confirm" while recording to control the form by voice.
3. Watch the status bar and warning banner for processing progress and vitals validation issues.
4. Press **Save & New Patient** to commit the current record (after confirming in the dialog) and start a fresh form.
5. Use ** Saved Patients** on the right to reload any previously saved patient into the form.
6. Check the ** Notes** and **Transcript** tabs to review the AI-generated notes and raw transcript for the most recently processed audio.
7. Use ** Upload Audio** to process a pre-recorded audio file instead of recording live.

> **Note:** Patient records are stored in-session only (in memory) — closing the app clears the saved patient list.

## File Structure

```
notesApp/
├── main.py            # App entry point — UI, form logic, event handling
├── workers.py          # Background threads: audio recording, transcription/extraction, vitals validation
├── theme.py            # UI color palette and stylesheet (dark/light)
├── requirements.txt    # Python dependencies
└── .gitignore
```

- `output/` (generated at runtime) — stores generated notes and transcripts
- `venv/` — local virtual environment (not committed)
