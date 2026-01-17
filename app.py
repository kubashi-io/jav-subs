import os
import threading
from flask import Flask, jsonify, render_template, request

from downloader import (
    scan_videos,
    download_subtitle_from_subtitlecat
)

app = Flask(__name__)

CURRENT_STATUS = {
    "videos": [],
    "finished": True
}

def process_single_video(video):
    # Skip if subtitle already exists
    if video.get("has_sub"):
        video["status"] = "success"
        video["log"].append("Subtitle already exists. Skipped.")
        return True

    code = video["code"]
    file = video["file"]

    if not code:
        video["log"].append("No JAV code found.")
        return False

    video["log"].append(f"Searching SubtitleCat for {code}...")

    sub = download_subtitle_from_subtitlecat(code)

    if not sub:
        video["log"].append("No subtitle found.")
        return False

    srt_path = os.path.splitext(file)[0] + ".en.srt"

    try:
        with open(srt_path, "wb") as f:
            f.write(sub)
    except Exception as e:
        video["log"].append(f"Failed to save subtitle: {e}")
        return False

    video["log"].append(f"Saved to {srt_path}")
    return True

# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scan")
def scan():
    """
    Scans the directory and returns the list of videos.
    """
    global CURRENT_STATUS

    # Change this to your actual video directory
    VIDEO_DIR = "/videos"

    videos = scan_videos(VIDEO_DIR, include_existing=True)

    CURRENT_STATUS = {
        "videos": [
            {
                "file": v["file"],
                "code": v["code"],
                "has_sub": v["has_sub"],
                "status": "",
                "log": []
            }
            for v in videos
        ],
        "finished": True
    }

    return jsonify({"videos": CURRENT_STATUS["videos"]})


@app.route("/download", methods=["POST"])
def download():
    """
    Starts background download thread.
    """
    global CURRENT_STATUS
    CURRENT_STATUS["finished"] = False

    def run():
        for i, v in enumerate(CURRENT_STATUS["videos"]):
            CURRENT_STATUS["videos"][i]["status"] = "downloading"
            CURRENT_STATUS["videos"][i]["log"].append("Starting download...")

            ok = process_single_video(CURRENT_STATUS["videos"][i])

            if ok:
                CURRENT_STATUS["videos"][i]["status"] = "success"
                CURRENT_STATUS["videos"][i]["log"].append("Success!")
            else:
                CURRENT_STATUS["videos"][i]["status"] = "failed"
                CURRENT_STATUS["videos"][i]["log"].append("Failed.")

        CURRENT_STATUS["finished"] = True

    threading.Thread(target=run).start()

    return jsonify({"ok": True})


@app.route("/status")
def status():
    """
    Returns live status for the UI to poll.
    """
    return jsonify(CURRENT_STATUS)


# ------------------------------------------------------------
# Run the app
# ------------------------------------------------------------

