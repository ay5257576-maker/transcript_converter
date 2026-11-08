import os
import re
import tempfile
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from docx import Document
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "my-super-secret-key-9f3k2j8h"   # needed for flash messages

ALLOWED_EXTENSIONS = {"txt"}

# Matches timestamps in (MM:SS) or (M:SS) format
TIME_REGEX = re.compile(r'\((\d{1,2}):(\d{2})\)')


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def to_seconds(mm, ss):
    return int(mm) * 60 + int(ss)


def from_seconds(total_seconds):
    mm = total_seconds // 60
    ss = total_seconds % 60
    return f"({mm:02d}:{ss:02d})"


def extract_times(text):
    return [to_seconds(mm, ss) for mm, ss in TIME_REGEX.findall(text)]


def merge_transcripts(part1: str, part2: str) -> str:
    """
    Merge two transcript parts.
    All timestamps in Part 2 are shifted by the last timestamp of Part 1.
    """
    part1_times = extract_times(part1)
    offset = max(part1_times) if part1_times else 0

    def shift_timestamp(match):
        mm, ss = match.groups()
        original_seconds = to_seconds(mm, ss)
        new_seconds = original_seconds + offset
        return from_seconds(new_seconds)

    shifted_part2 = TIME_REGEX.sub(shift_timestamp, part2)
    merged_text = part1.rstrip() + "\n" + shifted_part2
    return merged_text


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


@app.route("/merge", methods=["POST"])
def merge():
    """Merge two transcript parts and return a .txt file."""
    if "part1" not in request.files or "part2" not in request.files:
        flash("Both Part 1 and Part 2 files are required")
        return redirect(url_for("index"))

    part1_file = request.files["part1"]
    part2_file = request.files["part2"]

    if part1_file.filename == "" or part2_file.filename == "":
        flash("Please select both files")
        return redirect(url_for("index"))

    if not (allowed_file(part1_file.filename) and allowed_file(part2_file.filename)):
        flash("Only .txt files are allowed")
        return redirect(url_for("index"))

    try:
        part1 = part1_file.read().decode("utf-8")
        part2 = part2_file.read().decode("utf-8")
    except Exception:
        flash("Could not read the uploaded files. Make sure they are valid UTF-8 text.")
        return redirect(url_for("index"))

    if not part1.strip() or not part2.strip():
        flash("One or both files are empty")
        return redirect(url_for("index"))

    merged_text = merge_transcripts(part1, part2)

    # Write to a temporary .txt file and send it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tmp:
        tmp.write(merged_text)
        tmp_path = tmp.name

    return send_file(
        tmp_path,
        as_attachment=True,
        download_name="merged_transcript.txt",
        mimetype="text/plain",
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
