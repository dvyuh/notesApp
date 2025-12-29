import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QProgressBar, QFileDialog, 
    QTabWidget, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# --- IMPORTS FROM OTHER FILES ---
from theme import COLORS, get_stylesheet
from workers import RecordingThread, ProcessingThread

class VoiceNotesApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.recording = False
        self.is_dark_mode = True
        self.processing_thread = None
        self.recording_thread = None
        
        self.init_ui()
        self.apply_theme()
        
    def init_ui(self):
        self.setWindowTitle("VoiceNotes Pro")
        self.resize(1100, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.layout = QVBoxLayout(main_widget)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("🎓 VoiceNotes Pro")
        self.title_label.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.theme_btn = QPushButton("🌙 Dark Mode")
        self.theme_btn.setFixedSize(120, 40)
        self.theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_btn)
        self.layout.addLayout(header_layout)

        # Status
        self.status_container = QFrame()
        self.status_container.setObjectName("status_container")
        status_layout = QHBoxLayout(self.status_container)
        self.status_label = QLabel("Ready to record")
        self.status_label.setFont(QFont("Segoe UI", 12))
        status_layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        status_layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.status_container)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 11))
        self.main_notes = QTextEdit()
        self.transcript_text = QTextEdit()
        self.tabs.addTab(self.main_notes, "📝 Smart Notes")
        self.tabs.addTab(self.transcript_text, "🗣️ Transcript")
        self.layout.addWidget(self.tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        self.record_btn = QPushButton("🎤 Start Recording")
        self.record_btn.setFixedHeight(55)
        self.record_btn.clicked.connect(self.toggle_recording)
        
        self.upload_btn = QPushButton("📤 Upload Audio")
        self.upload_btn.setFixedHeight(55)
        self.upload_btn.clicked.connect(self.upload_audio_file)
        
        btn_layout.addWidget(self.record_btn)
        btn_layout.addWidget(self.upload_btn)
        self.layout.addLayout(btn_layout)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.theme_btn.setText("☀️ Light Mode" if self.is_dark_mode else "🌙 Dark Mode")
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.is_dark_mode))
        if self.recording:
            self.record_btn.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; border-radius: 8px;")

    def toggle_recording(self):
        if not self.recording:
            self.recording = True
            self.record_btn.setText("⏹️ Stop Recording")
            self.record_btn.setStyleSheet(f"background-color: {COLORS['danger']}; color: white; border-radius: 8px;")
            self.status_label.setText("🎙️ Recording in progress...")
            self.progress_bar.setVisible(True)
            
            self.recording_thread = RecordingThread()
            self.recording_thread.completed.connect(self.on_recording_complete)
            self.recording_thread.start()
        else:
            self.recording = False
            self.record_btn.setText("🎤 Start Recording")
            self.apply_theme()
            if self.recording_thread:
                self.recording_thread.stop_recording()

    def upload_audio_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Audio", "", "Audio (*.mp3 *.wav *.m4a)")
        if path: self.start_processing(path)

    def on_recording_complete(self):
        self.start_processing("temp_audio.wav")

    def start_processing(self, file_path):
        self.status_label.setText("⚙️ Processing audio with AI...")
        self.progress_bar.setVisible(True)
        self.processing_thread = ProcessingThread(file_path)
        self.processing_thread.progress.connect(self.status_label.setText)
        self.processing_thread.finished.connect(self.on_processing_complete)
        self.processing_thread.error.connect(lambda e: self.status_label.setText(f"❌ Error: {e}"))
        self.processing_thread.start()

    def on_processing_complete(self, data):
        with open(data['notes_path'], 'r') as f: self.main_notes.setPlainText(f.read())
        with open(data['transcript_path'], 'r') as f: self.transcript_text.setPlainText(f.read())
        self.status_label.setText("✅ Notes Generated Successfully!")
        self.progress_bar.setVisible(False)
        self.record_btn.setEnabled(True)
        if os.path.exists("temp_audio.wav"):
            os.remove("temp_audio.wav")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = VoiceNotesApp()
    window.show()
    sys.exit(app.exec())