# main.py
"""
VoiceNotes Pro — Patient Intake Edition
=======================================
Hybrid voice + manual input for structured patient records.

Features
--------
* Per-field voice recording with "Active Listening" visual feedback.
* Override button on every field for manual typing correction.
* Multi-patient management with auto-incrementing Patient ID.
* Save & New Patient – clears form, stores record in session list.
* Keyword voice commands: "next field", "clear field", "confirm".
* Vitals validation with in-app warning banners.
* Confirmation overlay before committing a record.
* Dark / Light theme toggle.
"""

import sys
import os
import json
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QProgressBar,
    QFileDialog, QTabWidget, QFrame, QSplitter, QListWidget,
    QListWidgetItem, QScrollArea, QComboBox, QMessageBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from theme import COLORS, get_stylesheet
from workers import RecordingThread, ProcessingThread, ValidationWorker


# ── FieldRow ──────────────────────────────────────────────────────────────────
class FieldRow(QWidget):
    """
    A single labelled input row with:
      • a QLineEdit (or QComboBox for gender)
      • a 🎤 mic button to start/stop recording THIS field
      • an Override button toggling between read-only and editable
    """

    def __init__(self, label: str, field_name: str,
                 widget_type: str = "line",
                 choices: Optional[list] = None,
                 parent=None):
        super().__init__(parent)
        self.field_name   = field_name
        self._listening   = False
        self._overriding  = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        # Label
        lbl = QLabel(label)
        lbl.setFixedWidth(130)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setStyleSheet(f"color: {COLORS['muted_text']};")
        layout.addWidget(lbl)

        # Input widget
        if widget_type == "combo" and choices:
            self.input = QComboBox()
            self.input.addItems([""] + choices)
            self.input.setFixedHeight(34)
        else:
            self.input = QLineEdit()
            self.input.setPlaceholderText("Voice or type…")
            self.input.setFixedHeight(34)
            self.input.setReadOnly(True)   # starts locked; Override unlocks

        layout.addWidget(self.input, 1)

        # Override button
        self.override_btn = QPushButton("✏️ Override")
        self.override_btn.setObjectName("override_btn")
        self.override_btn.setFixedSize(88, 30)
        self.override_btn.setToolTip("Switch to manual typing for this field")
        self.override_btn.clicked.connect(self._toggle_override)
        layout.addWidget(self.override_btn)

        # Mic button (only for line edits, not combos)
        if widget_type != "combo":
            self.mic_btn = QPushButton("🎤")
            self.mic_btn.setFixedSize(36, 30)
            self.mic_btn.setToolTip("Record voice for this field")
            layout.addWidget(self.mic_btn)
        else:
            self.mic_btn = None

    # ── Public helpers ─────────────────────────────────────────────────
    def get_value(self) -> str:
        if isinstance(self.input, QComboBox):
            return self.input.currentText()
        return self.input.text()

    def set_value(self, value: str):
        if isinstance(self.input, QComboBox):
            idx = self.input.findText(value, Qt.MatchFlag.MatchFixedString)
            if idx >= 0:
                self.input.setCurrentIndex(idx)
        else:
            self.input.setText(value)

    def clear_value(self):
        if isinstance(self.input, QComboBox):
            self.input.setCurrentIndex(0)
        else:
            self.input.clear()

    def set_listening(self, active: bool):
        """Toggle the blue 'active listening' highlight."""
        self._listening = active
        if isinstance(self.input, QLineEdit):
            # Use dynamic property so QSS selector works
            self.input.setProperty("listening", "true" if active else "false")
            self.input.style().unpolish(self.input)
            self.input.style().polish(self.input)
            if active:
                self.input.setPlaceholderText("🎙️ Listening…")
            else:
                self.input.setPlaceholderText("Voice or type…")

    # ── Private ────────────────────────────────────────────────────────
    def _toggle_override(self):
        self._overriding = not self._overriding
        if isinstance(self.input, QLineEdit):
            self.input.setReadOnly(not self._overriding)
        self.override_btn.setProperty("active", "true" if self._overriding else "false")
        self.override_btn.style().unpolish(self.override_btn)
        self.override_btn.style().polish(self.override_btn)
        self.override_btn.setText("🔒 Lock" if self._overriding else "✏️ Override")
        if self._overriding and isinstance(self.input, QLineEdit):
            self.input.setFocus()


# ── ConfirmDialog ─────────────────────────────────────────────────────────────
class ConfirmDialog(QMessageBox):
    """Simple confirmation overlay shown before saving a patient."""

    def __init__(self, patient_name: str, warnings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Patient Record")
        self.setIcon(QMessageBox.Icon.Question)

        name_str = patient_name or "Unknown"
        msg = f"Save record for <b>{name_str}</b>?"
        if warnings:
            msg += "<br><br>⚠️ <b>Validation Warnings:</b><br>"
            for field, warn in warnings.items():
                msg += f"• {field}: {warn}<br>"
        self.setText(msg)

        self.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        self.setDefaultButton(QMessageBox.StandardButton.Yes)


# ── Main Window ───────────────────────────────────────────────────────────────
class VoiceNotesApp(QMainWindow):

    # All template fields in display order
    FIELD_DEFS = [
        # (label, field_name, widget_type, choices)
        ("Full Name",        "name",            "line",  None),
        ("Age",              "age",             "line",  None),
        ("Gender",           "gender",          "combo", ["Male", "Female", "Other"]),
        ("Blood Pressure",   "bp",              "line",  None),
        ("Heart Rate (bpm)", "heart_rate",      "line",  None),
        ("Temperature (°C)", "temperature",     "line",  None),
        ("Chief Complaint",  "chief_complaint", "line",  None),
        ("Allergies",        "allergies",       "line",  None),
        ("Diagnosis",        "diagnosis",       "line",  None),
    ]

    def __init__(self):
        super().__init__()
        self.is_dark_mode        = True
        self.patient_id          = 1
        self.patient_list        : list[dict] = []   # session-level store
        self.active_field_row    : Optional[FieldRow] = None
        self.recording_thread    : Optional[RecordingThread] = None
        self.processing_thread   : Optional[ProcessingThread] = None
        self._field_rows         : dict[str, FieldRow] = {}

        self._init_ui()
        self._apply_theme()

    # ── UI construction ────────────────────────────────────────────────
    def _init_ui(self):
        self.setWindowTitle("VoiceNotes Pro — Patient Intake")
        self.resize(1200, 860)

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Header bar ──────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(
            f"background-color: {COLORS['medium_blue']}; border: none;"
        )
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("🏥  VoiceNotes Pro — Patient Intake")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        h_layout.addWidget(title)
        h_layout.addStretch()

        self.patient_id_label = QLabel(f"Patient ID: #{self.patient_id:04d}")
        self.patient_id_label.setFont(QFont("Segoe UI", 12))
        self.patient_id_label.setStyleSheet(
            f"color: {COLORS['cream']}; padding-right: 20px;"
        )
        h_layout.addWidget(self.patient_id_label)

        self.theme_btn = QPushButton("☀️ Light")
        self.theme_btn.setFixedSize(90, 34)
        self.theme_btn.clicked.connect(self._toggle_theme)
        h_layout.addWidget(self.theme_btn)

        root_layout.addWidget(header)

        # ── Status bar ──────────────────────────────────────────────────
        self.status_container = QFrame()
        self.status_container.setObjectName("status_container")
        self.status_container.setFixedHeight(44)
        s_layout = QHBoxLayout(self.status_container)
        s_layout.setContentsMargins(16, 0, 16, 0)

        self.status_label = QLabel("Ready — select a field and press 🎤 to start.")
        self.status_label.setFont(QFont("Segoe UI", 11))
        s_layout.addWidget(self.status_label, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)       # indeterminate spinner
        self.progress_bar.setFixedWidth(140)
        self.progress_bar.setVisible(False)
        s_layout.addWidget(self.progress_bar)

        root_layout.addWidget(self.status_container)

        # ── Body ────────────────────────────────────────────────────────
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(16, 12, 16, 12)
        body_layout.setSpacing(12)

        # Left: form + controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # ── Section cards ────────────────────────────────────────────
        sections = [
            ("👤 Demographics", ["name", "age", "gender"]),
            ("📊 Vitals",        ["bp", "heart_rate", "temperature"]),
            ("📋 Clinical",      ["chief_complaint", "allergies", "diagnosis"]),
        ]
        field_def_map = {fd[1]: fd for fd in self.FIELD_DEFS}

        for section_title, field_names in sections:
            card = QFrame()
            card.setObjectName("section_card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(4)

            sec_lbl = QLabel(section_title)
            sec_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            card_layout.addWidget(sec_lbl)

            for fname in field_names:
                label, field_name, widget_type, choices = field_def_map[fname]
                row = FieldRow(label, field_name, widget_type, choices)
                self._field_rows[field_name] = row
                card_layout.addWidget(row)

                # Wire mic button per-field
                if row.mic_btn:
                    row.mic_btn.clicked.connect(
                        lambda checked, r=row: self._toggle_field_recording(r)
                    )

            left_layout.addWidget(card)

        # ── Warning banner (hidden until needed) ─────────────────────
        self.warning_banner = QLabel("")
        self.warning_banner.setWordWrap(True)
        self.warning_banner.setVisible(False)
        self.warning_banner.setStyleSheet(
            f"background-color: #4A1500; color: #FF9A7A; "
            f"border: 1px solid {COLORS['danger']}; border-radius: 6px; "
            f"padding: 8px; font-size: 12px;"
        )
        left_layout.addWidget(self.warning_banner)

        # ── Global controls ──────────────────────────────────────────
        ctrl_layout = QHBoxLayout()

        self.upload_btn = QPushButton("📤 Upload Audio")
        self.upload_btn.setFixedHeight(44)
        self.upload_btn.clicked.connect(self._upload_audio)
        ctrl_layout.addWidget(self.upload_btn)

        self.clear_btn = QPushButton("🗑️ Clear Form")
        self.clear_btn.setFixedHeight(44)
        self.clear_btn.clicked.connect(self._clear_form)
        ctrl_layout.addWidget(self.clear_btn)

        self.save_new_btn = QPushButton("💾 Save & New Patient")
        self.save_new_btn.setObjectName("save_new_btn")
        self.save_new_btn.setFixedHeight(44)
        self.save_new_btn.clicked.connect(self._save_and_new)
        ctrl_layout.addWidget(self.save_new_btn)

        left_layout.addLayout(ctrl_layout)
        left_layout.addStretch()

        body_layout.addWidget(left_panel, 3)

        # Right: patient list + notes tabs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        # Patient list
        list_card = QFrame()
        list_card.setObjectName("patient_list_panel")
        list_card_layout = QVBoxLayout(list_card)
        list_card_layout.setContentsMargins(12, 10, 12, 10)

        list_hdr = QHBoxLayout()
        list_title = QLabel("📂 Saved Patients (this session)")
        list_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        list_hdr.addWidget(list_title)
        list_hdr.addStretch()
        self.load_btn = QPushButton("📋 Load")
        self.load_btn.setFixedHeight(28)
        self.load_btn.setToolTip("Load selected patient into form")
        self.load_btn.clicked.connect(self._load_selected_patient)
        list_hdr.addWidget(self.load_btn)
        list_card_layout.addLayout(list_hdr)

        self.patient_list_widget = QListWidget()
        self.patient_list_widget.setFixedHeight(160)
        list_card_layout.addWidget(self.patient_list_widget)

        right_layout.addWidget(list_card)

        # Notes / transcript tabs
        self.tabs = QTabWidget()
        self.tabs.setFont(QFont("Segoe UI", 10))

        self.notes_text      = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setPlaceholderText("AI-generated notes will appear here…")

        self.transcript_text = QTextEdit()
        self.transcript_text.setReadOnly(True)
        self.transcript_text.setPlaceholderText("Raw transcript will appear here…")

        self.tabs.addTab(self.notes_text,      "📝 Notes")
        self.tabs.addTab(self.transcript_text, "🗣️ Transcript")

        right_layout.addWidget(self.tabs, 1)

        body_layout.addWidget(right_panel, 2)

        root_layout.addWidget(body, 1)

    # ── Theme ──────────────────────────────────────────────────────────
    def _toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.theme_btn.setText("🌙 Dark" if not self.is_dark_mode else "☀️ Light")
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.is_dark_mode))

    # ── Recording (per-field) ──────────────────────────────────────────
    def _toggle_field_recording(self, row: FieldRow):
        """Start or stop recording for a specific field row."""
        if self.active_field_row is row and self.recording_thread:
            # Stop recording this field
            self._stop_field_recording()
        else:
            if self.recording_thread:
                self._stop_field_recording()
            self._start_field_recording(row)

    def _start_field_recording(self, row: FieldRow):
        self.active_field_row = row
        row.set_listening(True)
        row.mic_btn.setText("⏹️")
        row.mic_btn.setStyleSheet(
            f"background-color: {COLORS['pulse_red']}; color: white; border-radius: 6px;"
        )
        self._set_status(f"🎙️ Recording — {row.field_name}… say 'next field' to move on.")
        self.progress_bar.setVisible(True)

        self.recording_thread = RecordingThread(
            output_path=f"temp_{row.field_name}.wav"
        )
        self.recording_thread.completed.connect(
            lambda path: self._on_field_recording_done(path, row)
        )
        self.recording_thread.start()

    def _stop_field_recording(self):
        if self.recording_thread:
            self.recording_thread.stop_recording()
            # Thread will emit completed() and call _on_field_recording_done

    def _on_field_recording_done(self, wav_path: str, row: FieldRow):
        row.set_listening(False)
        if row.mic_btn:
            row.mic_btn.setText("🎤")
            row.mic_btn.setStyleSheet("")
        self.progress_bar.setVisible(False)
        self.recording_thread = None

        if not wav_path or not os.path.exists(wav_path):
            self._set_status("⚠️ No audio captured.")
            return

        self._set_status(f"⚙️ Processing audio for '{row.field_name}'…")
        self.progress_bar.setVisible(True)

        self.processing_thread = ProcessingThread(
            audio_file=wav_path,
            patient_id=self.patient_id,
        )
        self.processing_thread.progress.connect(self._set_status)
        self.processing_thread.field_result.connect(self._on_field_extracted)
        self.processing_thread.command.connect(self._on_voice_command)
        self.processing_thread.finished.connect(self._on_processing_complete)
        self.processing_thread.error.connect(
            lambda e: self._set_status(f"❌ {e}")
        )
        self.processing_thread.start()

    # ── Upload whole audio ─────────────────────────────────────────────
    def _upload_audio(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "",
            "Audio Files (*.mp3 *.wav *.m4a *.ogg)"
        )
        if path:
            self._set_status("⚙️ Processing uploaded audio…")
            self.progress_bar.setVisible(True)
            self.processing_thread = ProcessingThread(
                audio_file=path,
                patient_id=self.patient_id,
            )
            self.processing_thread.progress.connect(self._set_status)
            self.processing_thread.field_result.connect(self._on_field_extracted)
            self.processing_thread.command.connect(self._on_voice_command)
            self.processing_thread.finished.connect(self._on_processing_complete)
            self.processing_thread.error.connect(
                lambda e: self._set_status(f"❌ {e}")
            )
            self.processing_thread.start()

    # ── Signal handlers ────────────────────────────────────────────────
    def _on_field_extracted(self, field_name: str, value: str):
        """Fill a field as soon as Ollama returns its value."""
        if field_name in self._field_rows:
            self._field_rows[field_name].set_value(value)

    def _on_voice_command(self, cmd: str):
        """Handle keyword voice commands emitted by the worker."""
        if cmd == "next_field":
            self._set_status("➡️ 'Next field' detected — moving on.")
            self._stop_field_recording()
        elif cmd == "clear_field" and self.active_field_row:
            self._set_status("🗑️ 'Clear field' detected — clearing.")
            self.active_field_row.clear_value()
        elif cmd == "confirm":
            self._set_status("✅ 'Confirm' detected — saving record.")
            self._save_and_new()

    def _on_processing_complete(self, data: dict):
        self.progress_bar.setVisible(False)

        # Show warnings banner
        warnings = data.get("_warnings", {})
        if warnings:
            lines = [f"⚠️ {f}: {m}" for f, m in warnings.items()]
            self.warning_banner.setText("\n".join(lines))
            self.warning_banner.setVisible(True)
        else:
            self.warning_banner.setVisible(False)

        # Populate notes + transcript tabs
        notes_path = data.get("notes_path", "")
        trans_path = data.get("transcript_path", "")
        if notes_path and os.path.exists(notes_path):
            with open(notes_path, "r", encoding="utf-8") as f:
                self.notes_text.setPlainText(f.read())
        if trans_path and os.path.exists(trans_path):
            with open(trans_path, "r", encoding="utf-8") as f:
                self.transcript_text.setPlainText(f.read())

        self._set_status("✅ Fields populated — review and press 'Save & New'.")

        # Clean up temp wav
        wav = data.get("audio_file", "")
        if wav and wav.startswith("temp_") and os.path.exists(wav):
            os.remove(wav)

    # ── Patient management ─────────────────────────────────────────────
    def _collect_form_data(self) -> dict:
        return {fname: self._field_rows[fname].get_value()
                for fname in self._field_rows}

    def _clear_form(self):
        for row in self._field_rows.values():
            row.clear_value()
        self.warning_banner.setVisible(False)
        self.notes_text.clear()
        self.transcript_text.clear()

    def _save_and_new(self):
        data = self._collect_form_data()
        # Validate vitals before confirm dialog
        warnings = ValidationWorker.validate_vitals(data)

        dlg = ConfirmDialog(data.get("name", ""), warnings, parent=self)
        if dlg.exec() != QMessageBox.StandardButton.Yes:
            return

        # Store in session list
        data["_patient_id"] = self.patient_id
        self.patient_list.append(data)

        # Add to sidebar list widget
        display = (
            f"#{self.patient_id:04d}  {data.get('name') or 'Unknown'}  "
            f"— {data.get('chief_complaint') or 'No complaint'}"
        )
        item = QListWidgetItem(display)
        item.setData(Qt.ItemDataRole.UserRole, len(self.patient_list) - 1)
        self.patient_list_widget.addItem(item)

        self.patient_id += 1
        self.patient_id_label.setText(f"Patient ID: #{self.patient_id:04d}")

        self._clear_form()
        self._set_status(f"✅ Patient #{self.patient_id - 1:04d} saved. Ready for next patient.")

    def _load_selected_patient(self):
        selected = self.patient_list_widget.selectedItems()
        if not selected:
            self._set_status("⚠️ Select a patient from the list first.")
            return
        idx = selected[0].data(Qt.ItemDataRole.UserRole)
        data = self.patient_list[idx]
        for fname, row in self._field_rows.items():
            row.set_value(str(data.get(fname, "")))
        self._set_status(f"📋 Loaded patient #{data.get('_patient_id', '?'):04d}.")

    # ── Helpers ────────────────────────────────────────────────────────
    def _set_status(self, msg: str):
        self.status_label.setText(msg)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    window = VoiceNotesApp()
    window.show()
    sys.exit(app.exec())