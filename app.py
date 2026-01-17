import os
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify
from downloader import run_downloader, scan_videos

app = Flask(__name__)

LOG_FILE = "jav_subtitle_downloader.log"
BUILD_SHA = os.environ.get("BUILD_SHA", "unknown")[:7]

STATUS = {
    "total": 0,
    "processed": 0,
    "downloaded": 0,
    "failed": 0,
    "running": False,
    "start_time": None
}


@app.route("/", methods=["GET"])
def index():
    root_dir = os.environ.get("VIDEO_ROOT_DIR", "/videos")

    logs = ""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = f.read()

    return render_template(
        "index.html",
        root_dir=root_dir,
        logs=logs,
        build_sha=BUILD_SHA
    )


@app.route("/preview", methods=["POST"])
def preview():
    root_dir = request.form.get("root_dir")
    include_existing = request.form.get("include_existing_subs") == "on"

    files = scan_videos(root_dir, include_existing=include_existing)

    return render_template(
        "preview.html",
        files=files,
        root_dir=root_dir,
        build_sha=BUILD_SHA
    )


@app.route("/start", methods=["POST"])
def start():
    root_dir = request.form.get("root_dir")
    multithread = request.form.get("multithread") == "on"
    max_threads = int(request.form.get("max_threads") or 10)
    test_mode = request.form.get("test_mode") == "on"
    include_existing = request.form.get("include_existing_subs") == "on"

    STATUS.update({
        "total": 0,
        "processed": 0,
        "downloaded": 0,
        "failed": 0,
        "running": True,
        "start_time": time.time()
    })

    run_downloader(
        root_dir,
        use_multithreading=multithread,
        max_threads=max_threads,
        test_mode=test_mode,
        include_existing=include_existing,
        status=STATUS
    )

    STATUS["running"] = False
    return redirect(url_for("index"))


@app.route("/status")
def status():
    return jsonify(STATUS)


@app.route("/health")
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=16969)
