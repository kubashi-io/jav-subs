import os
import threading
from flask import Flask, jsonify, render_template

from downloader import (
    scan_videos,
    download_subtitle_from_subtitlecat
)

app = Flask(__name__)

# Global status shared with UI
CURRENT_STATUS = {
    "videos": [],
    "finished": True
}


# ------------------------------------------------------------
# Process a single video (UI-friendly wrapper)
# ------------------------------------------------------------
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

    result = download_subtitle_from_subtitlecat(code)

    if not result:
        video["log"].append("No subtitle found.")
        return False

    # Log metadata from downloader
    if "title" in result:
        video["log"].append(f"Found subtitle: {result['title']}")
    if "source" in result:
        video["log"].append(f"Source: {result['source']}")

    # Save as .en.srt
    srt_path = os.path.splitext(file)[0] + ".en.srt"

    try:
        with open(srt_path, "wb") as f:
            f.write(result["bytes"])
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
    global CURRENT_STATUS

    # Update this to your real directory
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
    return jsonify(CURRENT_STATUS)
