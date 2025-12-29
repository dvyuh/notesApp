# workers.py
import os
import datetime
import json
import re
import warnings
from pathlib import Path
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
import whisper
import ollama
from PyQt6.QtCore import QThread, pyqtSignal

# Settings
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
            self.progress.emit("✍️ Transcribing audio...")
            model = whisper.load_model(MODEL_SIZE, device="cpu")
            result = model.transcribe(self.audio_file, fp16=False)
            raw_text = result['text'].strip()
            segments = result.get('segments', [])

            if not raw_text: raise Exception("No speech detected.")

            self.progress.emit("🤖 Analyzing content...")
            multi_notes = self._generate_multi_layer_notes(raw_text)
            
            self.progress.emit("📚 Extracting concepts...")
            concepts = self._extract_concepts(raw_text)
            
            self.progress.emit("💾 Saving files...")
            output_data = self._save_outputs(raw_text, multi_notes, concepts, segments)
            
            self.finished.emit(output_data)
        except Exception as e:
            self.error.emit(str(e))

    # Paste all your helper methods (_generate_multi_layer_notes, etc.) here...
    # (Keeping it short for this example, but move the full logic functions here)
    
    def _generate_multi_layer_notes(self, text):
        # ... your existing code ...
        return {'tldr': "Mock Summary", 'key_ideas': "Mock Ideas"} 

    def _extract_concepts(self, text):
        return ["Concept A", "Concept B"]

    def _save_outputs(self, raw_text, multi_notes, concepts, segments):
        # ... your existing save logic ...
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        notes_path = output_dir / f"notes_{ts}.md"
        transcript_path = output_dir / f"transcript_{ts}.md"
        
        with open(notes_path, "w") as f: f.write("Your Notes Content")
        with open(transcript_path, "w") as f: f.write("Your Transcript Content")
            
        return {'notes_path': str(notes_path), 'transcript_path': str(transcript_path)}