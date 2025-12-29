import sys
import os
import warnings
import datetime
import json
import re
from pathlib import Path

# Suppress warnings
os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings("ignore")

import whisper
import ollama
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QProgressBar, QFileDialog, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

# --- SETTINGS ---
MODEL_SIZE = "tiny"
OLLAMA_MODEL = "mistral"
FS = 16000

class RecordingThread(QThread):
    """Handles audio recording in background thread"""
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
    """Handles audio processing and AI note generation"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, audio_file):
        super().__init__()
        self.audio_file = audio_file

    def run(self):
        try:
            # 1. Transcription
            self.progress.emit("✍️ Transcribing audio...")
            model = whisper.load_model(MODEL_SIZE, device="cpu")
            result = model.transcribe(self.audio_file, fp16=False)
            raw_text = result['text'].strip()
            segments = result.get('segments', [])

            if not raw_text:
                raise Exception("No speech detected in the audio.")

            # 2. AI Processing
            self.progress.emit("🤖 Generating multi-layer notes...")
            multi_notes = self._generate_multi_layer_notes(raw_text)
            
            self.progress.emit("📚 Extracting concepts and examples...")
            concepts = self._extract_concepts(raw_text)
            examples = self._extract_examples(raw_text)
            quotes = self._extract_quotes(raw_text)
            knowledge_gaps = self._detect_knowledge_gaps(raw_text)
            
            self.progress.emit("🏗️ Detecting structure...")
            structure = self._detect_structure(raw_text)
            
            self.progress.emit("🔗 Generating concept graph...")
            concept_graph = self._generate_concept_graph(concepts)
            
            # 3. Save outputs
            self.progress.emit("💾 Saving files...")
            output_data = self._save_outputs(
                raw_text, multi_notes, concepts, examples, quotes,
                knowledge_gaps, structure, concept_graph, segments
            )
            
            self.finished.emit(output_data)
            
        except Exception as e:
            self.error.emit(str(e))

    def _safe_parse_list(self, content, limit=5):
        """Prevents 'unhashable type: slice' by ensuring we have a list before slicing."""
        try:
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if isinstance(data, list):
                    return data[:limit]
            # Fallback to line splitting
            lines = [l.strip("- ").strip() for l in content.split('\n') if l.strip()]
            return lines[:limit]
        except:
            return []

    def _generate_multi_layer_notes(self, text):
        prompts = {
            'tldr': f"Create a brief TL;DR (2-3 sentences) of:\n\n{text}",
            'key_ideas': f"List 3-5 key ideas from:\n\n{text}",
            'intuition': f"Explain the intuition/why this matters:\n\n{text}",
            'exam_traps': f"What are common misconceptions related to:\n\n{text}"
        }
        notes = {}
        for layer, prompt in prompts.items():
            try:
                response = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
                notes[layer] = response['message']['content']
            except:
                notes[layer] = "Error generating content."
        return notes

    def _extract_concepts(self, text):
        prompt = f"Extract 5-10 key concepts from this text. Return ONLY a JSON list of strings.\n\n{text}"
        res = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        return self._safe_parse_list(res['message']['content'], 10)

    def _extract_examples(self, text):
        prompt = f"Extract examples or analogies from this text. Return ONLY a JSON list of strings.\n\n{text}"
        res = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        return self._safe_parse_list(res['message']['content'], 5)

    def _extract_quotes(self, text):
        prompt = f"Extract 2-3 important quotes. Return ONLY a JSON list of strings.\n\n{text}"
        res = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
        return self._safe_parse_list(res['message']['content'], 3)

    def _detect_knowledge_gaps(self, text):
        res = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': f"Potential gaps in: {text}"}])
        return res['message']['content']

    def _detect_structure(self, text):
        lines = text.split('.')
        return {'headings': [l[:50] for l in lines[:2]], 'subheadings': []}

    def _generate_concept_graph(self, concepts):
        if not concepts: return {'edges': []}
        prompt = f"For these concepts: {concepts}, return a JSON object with a key 'edges' containing relationship strings."
        try:
            res = ollama.chat(model=OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
            match = re.search(r'\{.*\}', res['message']['content'], re.DOTALL)
            return json.loads(match.group()) if match else {'edges': []}
        except:
            return {'edges': []}

    def _save_outputs(self, raw_text, multi_notes, concepts, examples, quotes, 
                      knowledge_gaps, structure, concept_graph, segments):
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        notes_path = output_dir / f"notes_{ts}.md"
        transcript_path = output_dir / f"transcript_{ts}.md"
        
        main_content = f"# Notes\n\n## 🎯 TL;DR\n{multi_notes.get('tldr')}\n\n## 💡 Key Ideas\n{multi_notes.get('key_ideas')}\n\n"
        main_content += "## 🔑 Concepts\n" + "\n".join([f"- {c}" for c in concepts])
        
        with open(notes_path, "w") as f: f.write(main_content)
        
        with open(transcript_path, "w") as f:
            for s in segments:
                f.write(f"[{int(s['start']//60):02}:{int(s['start']%60):02}] {s['text']}\n\n")

        return {
            'notes_path': str(notes_path),
            'transcript_path': str(transcript_path),
            'concepts': concepts,
            'examples': examples,
            'quotes': quotes
        }

class VoiceNotesApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.recording = False
        self.processing_thread = None
        self.recording_thread = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Advanced Voice to Notes")
        self.setGeometry(100, 100, 1000, 700)
        self.setStyleSheet(self.get_stylesheet())
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        title = QLabel("🎓 Voice to Notes")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        btn_layout = QHBoxLayout()
        self.record_btn = QPushButton("🎤 Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        self.upload_btn = QPushButton("📤 Upload Audio")
        self.upload_btn.clicked.connect(self.upload_audio_file)
        btn_layout.addWidget(self.record_btn)
        btn_layout.addWidget(self.upload_btn)
        layout.addLayout(btn_layout)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.tabs = QTabWidget()
        self.main_notes = QTextEdit(readOnly=True)
        self.transcript_text = QTextEdit(readOnly=True)
        self.tabs.addTab(self.main_notes, "📝 Notes")
        self.tabs.addTab(self.transcript_text, "📄 Transcript")
        layout.addWidget(self.tabs)

    def toggle_recording(self):
        if not self.recording:
            self.recording = True
            self.record_btn.setText("⏹️ Stop")
            self.status_label.setText("Recording...")
            self.progress_bar.setVisible(True)
            self.recording_thread = RecordingThread()
            self.recording_thread.completed.connect(self.on_recording_complete)
            self.recording_thread.start()
        else:
            self.recording = False
            self.record_btn.setText("🎤 Start Recording")
            if self.recording_thread:
                self.recording_thread.stop_recording()

    def upload_audio_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Audio", "", "Audio (*.mp3 *.wav *.m4a)")
        if path: self.start_processing(path)

    def on_recording_complete(self):
        self.start_processing("temp_audio.wav")

    def start_processing(self, file_path):
        self.status_label.setText("Processing...")
        self.progress_bar.setVisible(True)
        self.processing_thread = ProcessingThread(file_path)
        self.processing_thread.progress.connect(self.status_label.setText)
        self.processing_thread.finished.connect(self.on_processing_complete)
        self.processing_thread.error.connect(lambda e: self.status_label.setText(f"Error: {e}"))
        self.processing_thread.start()

    def on_processing_complete(self, data):
        with open(data['notes_path'], 'r') as f: self.main_notes.setPlainText(f.read())
        with open(data['transcript_path'], 'r') as f: self.transcript_text.setPlainText(f.read())
        self.status_label.setText("Done!")
        self.progress_bar.setVisible(False)

    def get_stylesheet(self):
        return "QPushButton { height: 40px; background: #2196F3; color: white; border-radius: 5px; font-weight: bold; } QTextEdit { background: white; border: 1px solid #ccc; }"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VoiceNotesApp()
    window.show()
    sys.exit(app.exec())