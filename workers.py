# workers.py
import os
import datetime
import json
from pathlib import Path
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import whisper
import ollama
from PyQt6.QtCore import QThread, pyqtSignal

# Setting
MODEL_SIZE = "tiny"
OLLAMA_MODEL = "mistral"
FS = 16000

class RecordingThread(QThread):
    completed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_recording = True
        self.fs = FS
        self.filename = "temp_audio.wav"
        self.frames = []

    def run(self):
        self.frames = []
        def callback(indata, frames, time, status):
            if self.is_recording:
                self.frames.append(indata.copy())

        with sd.InputStream(samplerate=self.fs, channels=1, callback=callback):
            while self.is_recording:
                self.msleep(100)
        
        if self.frames:
            recording_array = np.concatenate(self.frames, axis=0)
            # Normalize to 16-bit PCM for Whisper
            recording_array = (recording_array * 32767).astype(np.int16)
            write(self.filename, self.fs, recording_array)
            self.completed.emit()

    def stop_recording(self):
        self.is_recording = False

class ProcessingThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, audio_file):
        super().__init__()
        self.audio_file = audio_file

    def run(self):
        try:
            self.progress.emit("✍️ Transcribing audio (Whisper)...")
            # Load model (consider moving this to __init__ if doing multiple runs)
            model = whisper.load_model(MODEL_SIZE, device="cpu")
            result = model.transcribe(self.audio_file, fp16=False)
            raw_text = result['text'].strip()

            if not raw_text: 
                raise Exception("No speech detected in audio.")

            self.progress.emit(f"🤖 AI is thinking ({OLLAMA_MODEL})...")
            summary_notes = self._generate_notes_with_ollama(raw_text)
            
            self.progress.emit("💾 Saving files...")
            output_data = self._save_outputs(raw_text, summary_notes)
            
            self.finished.emit(output_data)
        except Exception as e:
            self.error.emit(str(e))

    def _generate_notes_with_ollama(self, text):
        """Sends the transcript to Ollama for summarization."""
        prompt = f"""
        Please provide structured study notes for the following transcript. 
        Include a 'Summary' section and a 'Key Takeaways' bulleted list.
        
        Transcript:
        {text}
        """
        try:
            response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
            return response['response']
        except Exception as e:
            return f"Ollama Error: {str(e)}"

    def _save_outputs(self, raw_text, summary_notes):
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        notes_path = output_dir / f"notes_{ts}.md"
        transcript_path = output_dir / f"transcript_{ts}.md"
        
        # Save the actual AI generated notes
        with open(notes_path, "w", encoding="utf-8") as f:
            f.write(f"# Study Notes - {ts}\n\n{summary_notes}")
            
        # Save the raw transcript
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(f"# Raw Transcript - {ts}\n\n{raw_text}")
            
        return {
            'notes_path': str(notes_path), 
            'transcript_path': str(transcript_path)
        }