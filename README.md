# 🎓 VoiceNotes Pro: AI-Powered Study Companion

A professional-grade desktop application that transforms audio recordings and lectures into structured, multi-layered study notes using **OpenAI Whisper** and **Ollama (Mistral)**.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![AI](https://img.shields.io/badge/AI-Whisper%20%2B%20Ollama-purple)

## 🚀 Key Features

* **🎙️ Live Recording & Upload:** Record lectures directly within the app or upload existing audio files (`.mp3`, `.wav`, `.m4a`).
* **🌗 Professional UI:** Modern, responsive interface with a built-in **Dark/Light Mode** toggle.
* **🧠 Multi-Layer Analysis:** Goes beyond simple transcription to generate:
    * **TL;DR Summaries:** Quick executive summaries.
    * **Key Concepts:** Extraction of technical terms and definitions.
    * **Exam Traps:** Identifies common misconceptions in the material.
* **📂 Structured Output:** Automatically organizes notes, raw transcripts, and audio data into a dedicated `output/` folder.
* **⚡ Local Processing:** Runs entirely on your machine for privacy—no data is sent to the cloud.

---

## 🛠️ System Requirements

Before running the app, ensure you have the following installed:

1.  **Python 3.9+**
2.  **FFmpeg:** Required for audio processing.
    * **Mac:** `brew install ffmpeg`
    * **Windows:** [Download FFmpeg](https://ffmpeg.org/download.html) and add to PATH.
3.  **Ollama:** Required for the AI generation.
    * Download from [ollama.com](https://ollama.com).
    * Run this command in your terminal to pull the model:
        ```bash
        ollama run mistral
        ```

---

## 📦 Installation & Setup

Follow these steps to set up the project cleanly.

### 1. Clone the Project
Download the project files to your local machine and navigate into the folder:
```bash
cd VoiceNotesPro