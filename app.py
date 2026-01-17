import os
import time
import logging
from logging.handlers import RotatingFileHandler

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


def setup_logging():
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3
    )
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Avoid adding multiple handlers if reloaded
    if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)


setup_logging()
logger = logging.getLogger(__name__)


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

    logger.info(f"Preview requested for root_dir={root_dir}, include_existing={include_existing}")

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

    logger.info(
        f"Download started: root_dir={root_dir}, multithread={multithread}, "
        f"max_threads={max_threads}, test_mode={test_mode}, include_existing={include_existing}"
    )

    STATUS.update({
        "total": 0,
        "processed": 0,
        "downloaded": 0,
        "failed": 0,
        "running": True,
        "start_time": time.time()
    })

    try:
        run_downloader(
            root_dir,
            use_multithreading=multithread,
            max_threads=max_threads,
            test_mode=test_mode,
            include_existing=include_existing,
            status=STATUS
        )
    except Exception as e:
        logger.exception(f"Error during download run: {e}")
    finally:
        STATUS["running"] = False
        logger.info("Download run finished")

    return redirect(url_for("index"))


@app.route("/status")
def status():
    return jsonify(STATUS)


@app.route("/health")
def health():
    return "OK", 200
