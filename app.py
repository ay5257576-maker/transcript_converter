import os
import re
import tempfile
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from docx import Document
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "my-super-secret-key-9f3k2j8h"   # needed for flash messages

ALLOWED_EXTENSIONS = {"txt"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def format_timestamp(ts):
    """Convert timestamps like 0:07 → 00:00:07 or 1:23 → 00:01:23"""
    parts = ts.split(":")
    if len(parts) == 2:
        minutes, seconds = map(int, parts)
        return f"00:{minutes:02d}:{seconds:02d}"
    elif len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return ts


def process_transcript(text: str, heading: str) -> Document:
    """Parse the transcript text and return a python-docx Document."""
    pattern = r"\((\d{1,2}:\d{2})\)\s*(.*?)(?=\s*\(\d{1,2}:\d{2}\)|$)"
    matches = re.findall(pattern, text, flags=re.DOTALL)

    rows = []
    for i in range(len(matches) - 1):
        t1_raw, dialogue = matches[i]
        t2_raw = matches[i + 1][0]
        t1 = format_timestamp(t1_raw)
        t2 = format_timestamp(t2_raw)
        dialogue = dialogue.strip().replace("\n", " ")
        rows.append([t1, t2, "Scene 1", "Unknown", dialogue])

    # Last entry (no end timestamp)
    if matches:
        last_t1 = format_timestamp(matches[-1][0])
        last_dialogue = matches[-1][1].strip().replace("\n", " ")
        rows.append([last_t1, "", "Scene 1", "Unknown", last_dialogue])

    # Build the Word document
    doc = Document()
    doc.add_heading(heading or "Transcript", level=1)

    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"

    headers = ["Timestamp1", "Timestamp2", "Scene", "Character", "Dialogue"]
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h

    for row in rows:
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = val

    return doc


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Validate file
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files["file"]
        heading = request.form.get("heading", "").strip() or "Transcript"

        if file.filename == "":
            flash("No file selected")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("Only .txt files are allowed")
            return redirect(request.url)

        # Read and process
        text = file.read().decode("utf-8").strip()
        if not text:
            flash("The uploaded file is empty")
            return redirect(request.url)

        doc = process_transcript(text, heading)

        # Save to a temporary file and send it
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
            doc.save(tmp.name)
            tmp_path = tmp.name

        download_name = secure_filename(file.filename.rsplit(".", 1)[0]) + ".docx"

        return send_file(
            tmp_path,
            as_attachment=True,
            download_name=download_name,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
