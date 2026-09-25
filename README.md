# Transcript → DOCX Converter

A small Flask web app that converts timestamped transcript text files into a formatted Word document.

## Features
- Upload a `.txt` file
- Custom document heading
- Generates a table with Timestamp1, Timestamp2, Scene, Character, Dialogue
- Instant download of the `.docx` file

## Setup

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Open http://127.0.0.1:5000 in your browser.

## Expected input format
```
(0:07) Hello everyone
(0:15) Welcome to the house
(1:02) Let’s begin
```

Timestamps can be `M:SS` or `H:MM:SS`.
