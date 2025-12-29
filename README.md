# Voice Notes App

A simple desktop app that records audio and generates notes from it.

## File Structure

- `main.py` – app entry point
- `workers.py` – background processing (audio → text)
- `theme.py` – UI styling
- `output/` – generated notes and transcripts
- `venv/` – virtual environment (not committed)

## Requirements
- Python 3.9+
- pip
- A working microphone

## Setup

1. Create a virtual environment
```bash
python3 -m venv venv
```

2. Activate the virtual environment
macOS / Linux
```source venv/bin/activate
```
Windows
```venv\Scripts\activate
```

3. Install dependencies
```pip install -r requirements.txt
```

4. Run
```python main.py
```