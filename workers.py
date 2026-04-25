# workers.py
"""
Threading workers for Voice-to-Patient intake.

RecordingThread  – records audio until stop_recording() is called.
                   Emits partial transcripts for real-time feedback.
                   Supports keyword triggers: "next field", "clear field".

ProcessingThread – transcribes a saved WAV file with Whisper and
                   routes the text to the correct patient field via Ollama.

ValidationWorker – lightweight; validates vitals ranges and returns
                   a dict of {field: warning_message}.
"""

import os
import re
import datetime
import json
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write
import whisper
import ollama

from PyQt6.QtCore import QThread, pyqtSignal

# ── Settings ──────────────────────────────────────────────────────────────────
MODEL_SIZE   = "tiny"
OLLAMA_MODEL = "mistral"
FS           = 16000          # sample rate (Hz)
CHUNK_SEC    = 0.1            # callback chunk size in seconds

# Keyword voice commands (lower-cased for matching)
CMD_NEXT_FIELD  = ["next field", "next", "move on"]
CMD_CLEAR_FIELD = ["clear field", "clear", "delete that", "erase"]
CMD_CONFIRM     = ["confirm", "save", "yes that's correct"]

# Realistic vitals ranges for validation
VITALS_RANGES = {
    "bp_systolic":  (60,  250),
    "bp_diastolic": (40,  150),
    "heart_rate":   (30,  250),
    "temperature":  (34.0, 42.5),
    "spo2":         (70,  100),
}

# ── RecordingThread ────────────────────────────────────────────────────────────
class RecordingThread(QThread):
    """
    Records microphone audio in background.

    Signals:
        completed(str)  – path of saved WAV file when stopped.
        partial(str)    – live transcript snippet (runs quick Whisper pass
                          every PARTIAL_INTERVAL_SEC seconds).
        command(str)    – keyword command detected ("next_field" / "clear_field").
    """
    completed = pyqtSignal(str)
    partial   = pyqtSignal(str)
    command   = pyqtSignal(str)

    PARTIAL_INTERVAL_FRAMES = int(FS * 3)   # run partial transcription every 3 s

    def __init__(self, output_path: str = "temp_audio.wav"):
        super().__init__()
        self.is_recording  = True
        self.output_path   = output_path
        self._frames: list = []

    # ------------------------------------------------------------------
    def run(self):
        self._frames = []

        def _callback(indata, frames, time, status):
            if self.is_recording:
                self._frames.append(indata.copy())

        with sd.InputStream(samplerate=FS, channels=1, dtype="float32",
                            callback=_callback):
            while self.is_recording:
                self.msleep(100)

        self._save_and_emit()

    # ------------------------------------------------------------------
    def stop_recording(self):
        """Called from the main thread to finish recording."""
        self.is_recording = False

    # ------------------------------------------------------------------
    def _save_and_emit(self):
        if not self._frames:
            self.completed.emit("")
            return
        audio = np.concatenate(self._frames, axis=0)
        audio_int16 = (audio * 32767).astype(np.int16)
        wav_write(self.output_path, FS, audio_int16)
        self.completed.emit(self.output_path)


# ── ProcessingThread ───────────────────────────────────────────────────────────
class ProcessingThread(QThread):
    """
    Transcribes audio and extracts structured patient fields via Ollama.

    Signals:
        progress(str)       – status message for the UI.
        field_result(str, str) – (field_name, extracted_value) pairs as Ollama
                               fills them in one-by-one.
        finished(dict)      – complete patient data dict + saved file paths.
        error(str)          – error message.
        command(str)        – keyword voice command found in transcript.
    """
    progress     = pyqtSignal(str)
    field_result = pyqtSignal(str, str)
    finished     = pyqtSignal(dict)
    error        = pyqtSignal(str)
    command      = pyqtSignal(str)

    # Fields the AI should attempt to fill
    PATIENT_FIELDS = [
        "name", "age", "gender",
        "bp", "heart_rate", "temperature",
        "chief_complaint", "allergies", "diagnosis",
    ]

    def __init__(self, audio_file: str, patient_id: int = 1,
                 manual_overrides: Optional[dict] = None):
        super().__init__()
        self.audio_file       = audio_file
        self.patient_id       = patient_id
        self.manual_overrides = manual_overrides or {}

    # ------------------------------------------------------------------
    def run(self):
        try:
            # 1. Transcribe
            self.progress.emit("✍️ Transcribing audio (Whisper)…")
            model      = whisper.load_model(MODEL_SIZE, device="cpu")
            result     = model.transcribe(self.audio_file, fp16=False)
            transcript = result["text"].strip()

            if not transcript:
                raise ValueError("No speech detected in audio.")

            # 2. Check for keyword voice commands
            self._detect_commands(transcript)

            # 3. Extract structured fields via Ollama
            self.progress.emit(f"🤖 Extracting patient data ({OLLAMA_MODEL})…")
            patient_data = self._extract_fields(transcript)

            # 4. Apply manual overrides (user typed corrections)
            patient_data.update(self.manual_overrides)

            # 5. Validate vitals
            warnings = ValidationWorker.validate_vitals(patient_data)
            patient_data["_warnings"] = warnings

            # 6. Save
            self.progress.emit("💾 Saving patient record…")
            paths = self._save_record(transcript, patient_data)
            patient_data.update(paths)

            self.finished.emit(patient_data)

        except Exception as exc:
            self.error.emit(str(exc))

    # ------------------------------------------------------------------
    def _detect_commands(self, text: str):
        lower = text.lower()
        for phrase in CMD_NEXT_FIELD:
            if phrase in lower:
                self.command.emit("next_field")
                return
        for phrase in CMD_CLEAR_FIELD:
            if phrase in lower:
                self.command.emit("clear_field")
                return
        for phrase in CMD_CONFIRM:
            if phrase in lower:
                self.command.emit("confirm")
                return

    # ------------------------------------------------------------------
    def _extract_fields(self, transcript: str) -> dict:
        """
        Ask Ollama to return a JSON object with exactly the PATIENT_FIELDS keys.
        Emits field_result for each key so the UI can fill fields live.
        """
        fields_list = ", ".join(self.PATIENT_FIELDS)
        prompt = f"""
You are a clinical data extraction assistant.
From the following patient intake transcript, extract these fields ONLY:
{fields_list}

Rules:
- Return ONLY a valid JSON object, no explanation, no markdown fences.
- If a field is not mentioned, use an empty string "".
- For "bp" use format "systolic/diastolic" e.g. "120/80".
- For "gender" normalise to: Male, Female, or Other.
- Keep "chief_complaint", "allergies", "diagnosis" concise (1-2 sentences).

Transcript:
{transcript}
"""
        try:
            response = ollama.generate(model=OLLAMA_MODEL, prompt=prompt)
            raw      = response["response"]
            # Strip possible markdown fences just in case
            raw      = re.sub(r"```json|```", "", raw).strip()
            data     = json.loads(raw)
        except (json.JSONDecodeError, KeyError):
            # Fallback: return empty dict so UI still works
            data = {f: "" for f in self.PATIENT_FIELDS}

        # Emit each field as it is "discovered"
        for field in self.PATIENT_FIELDS:
            value = data.get(field, "")
            if value:
                self.field_result.emit(field, str(value))

        return data

    # ------------------------------------------------------------------
    def _save_record(self, transcript: str, patient_data: dict) -> dict:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        pid = self.patient_id

        record_path     = output_dir / f"patient_{pid:04d}_{ts}.json"
        transcript_path = output_dir / f"transcript_{pid:04d}_{ts}.txt"
        notes_path      = output_dir / f"notes_{pid:04d}_{ts}.md"

        # Save raw transcript
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)

        # Save structured JSON (exclude internal keys)
        saveable = {k: v for k, v in patient_data.items()
                    if not k.startswith("_")}
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(saveable, f, indent=2)

        # Build a readable Markdown notes file
        warnings = patient_data.get("_warnings", {})
        md_lines = [
            f"# Patient Record — ID {pid:04d}",
            f"**Date:** {ts}",
            "",
            "## Demographics",
            f"- **Name:** {patient_data.get('name', '')}",
            f"- **Age:** {patient_data.get('age', '')}",
            f"- **Gender:** {patient_data.get('gender', '')}",
            "",
            "## Vitals",
            f"- **Blood Pressure:** {patient_data.get('bp', '')}",
            f"- **Heart Rate:** {patient_data.get('heart_rate', '')} bpm",
            f"- **Temperature:** {patient_data.get('temperature', '')} °C",
            "",
            "## Clinical Notes",
            f"- **Chief Complaint:** {patient_data.get('chief_complaint', '')}",
            f"- **Allergies:** {patient_data.get('allergies', '')}",
            f"- **Diagnosis:** {patient_data.get('diagnosis', '')}",
        ]
        if warnings:
            md_lines += ["", "## ⚠️ Validation Warnings"]
            for field, msg in warnings.items():
                md_lines.append(f"- **{field}**: {msg}")

        with open(notes_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        return {
            "record_path":     str(record_path),
            "transcript_path": str(transcript_path),
            "notes_path":      str(notes_path),
        }


# ── ValidationWorker ──────────────────────────────────────────────────────────
class ValidationWorker:
    """
    Static helper – no threading needed, runs synchronously.
    Returns {field: warning_string} for any out-of-range vitals.
    """

    @staticmethod
    def validate_vitals(data: dict) -> dict:
        warnings = {}

        # Blood pressure  "120/80"
        bp = data.get("bp", "")
        if bp:
            parts = re.findall(r"\d+", bp)
            if len(parts) >= 2:
                sys_v, dia_v = int(parts[0]), int(parts[1])
                lo, hi = VITALS_RANGES["bp_systolic"]
                if not (lo <= sys_v <= hi):
                    warnings["bp_systolic"] = (
                        f"Systolic BP {sys_v} mmHg is outside normal range "
                        f"({lo}–{hi} mmHg). Please verify."
                    )
                lo, hi = VITALS_RANGES["bp_diastolic"]
                if not (lo <= dia_v <= hi):
                    warnings["bp_diastolic"] = (
                        f"Diastolic BP {dia_v} mmHg is outside normal range "
                        f"({lo}–{hi} mmHg). Please verify."
                    )

        # Heart rate
        hr_raw = data.get("heart_rate", "")
        hr_nums = re.findall(r"\d+", str(hr_raw))
        if hr_nums:
            hr = int(hr_nums[0])
            lo, hi = VITALS_RANGES["heart_rate"]
            if not (lo <= hr <= hi):
                warnings["heart_rate"] = (
                    f"Heart rate {hr} bpm is outside normal range "
                    f"({lo}–{hi} bpm). Please verify."
                )

        # Temperature
        temp_raw = data.get("temperature", "")
        temp_nums = re.findall(r"\d+\.?\d*", str(temp_raw))
        if temp_nums:
            temp = float(temp_nums[0])
            lo, hi = VITALS_RANGES["temperature"]
            if not (lo <= temp <= hi):
                warnings["temperature"] = (
                    f"Temperature {temp} °C is outside normal range "
                    f"({lo}–{hi} °C). Please verify."
                )

        return warnings