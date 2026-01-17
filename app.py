# app.py
import os
from flask import Flask, render_template_string, request, redirect, url_for
from downloader import run_downloader

LOG_FILE = "jav_subtitle_downloader.log"

app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>JAV Subtitle Downloader</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        label { display: block; margin-top: 10px; }
        textarea { width: 100%; height: 400px; font-family: monospace; }
        .btn { margin-top: 10px; padding: 6px 12px; }
    </style>
</head>
<body>
    <h1>JAV Subtitle Downloader</h1>

    <form method="post" action="{{ url_for('start') }}">
        <label>Root video folder (inside container):</label>
        <input type="text" name="root_dir" size="60" value="{{ root_dir or '' }}" required>

        <label>
            <input type="checkbox" name="multithread" {% if multithread %}checked{% endif %}>
            Use multithreading
        </label>

        <label>Max threads:</label>
        <input type="number" name="max_threads" value="{{ max_threads }}" min="1" max="64">

        <br>
        <button class="btn" type="submit">Start Download</button>
    </form>

    <h2>Logs</h2>
    <form method="get" action="{{ url_for('index') }}">
        <button class="btn" type="submit">Refresh Logs</button>
    </form>
    <textarea readonly>{{ logs }}</textarea>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    root_dir = os.environ.get("VIDEO_ROOT_DIR", "/videos")
    multithread = True
    max_threads = 10

    logs = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = f.read()

    return render_template_string(
        TEMPLATE,
        root_dir=root_dir,
        multithread=multithread,
        max_threads=max_threads,
        logs=logs
    )

@app.route("/start", methods=["POST"])
def start():
    root_dir = request.form.get("root_dir")
    multithread = request.form.get("multithread") == "on"
    max_threads = int(request.form.get("max_threads") or 10)

    # Run in same process (simple). For heavy use, you'd offload to a background worker.
    run_downloader(root_dir, use_multithreading=multithread, max_threads=max_threads)

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
