from flask import Flask, request, jsonify
import os
from downloader import download_subtitle

app = Flask(__name__)
VIDEO_DIR = os.environ.get("VIDEO_DIR", "/videos")


@app.route("/download", methods=["POST"])
def download():
    data = request.json
    code = data.get("code")
    file = data.get("file")

    log = []

    result = download_subtitle(code, log)

    if not result:
        return jsonify({"success": False, "log": log})

    srt_path = os.path.splitext(file)[0] + ".en.srt"
    with open(srt_path, "wb") as f:
        f.write(result["content"])

    log.append(f"Saved subtitle → {srt_path}")

    return jsonify({"success": True, "log": log})
