import os
import time
import threading

def extract_jav_code(filename):
    # Simple pattern: ABC-123
    import re
    match = re.search(r"[A-Za-z]{2,5}-\d{2,5}", filename)
    return match.group(0) if match else None


def scan_videos(root_dir):
    results = []
    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if f.lower().endswith((".mp4", ".mkv", ".avi")):
                full = os.path.join(root, f)
                code = extract_jav_code(f)
                has_sub = os.path.exists(os.path.splitext(full)[0] + ".srt")
                results.append({
                    "file": full,
                    "code": code,
                    "has_sub": has_sub
                })
    return results


def process_video(video, test_mode, status):
    status["processed"] += 1

    if video["has_sub"]:
        return

    if test_mode:
        status["downloaded"] += 1
        return

    # Simulate download
    time.sleep(1)
    status["downloaded"] += 1


def run_downloader(root_dir, use_multithreading=True, max_threads=10, test_mode=False, status=None):
    videos = scan_videos(root_dir)
    status["total"] = len(videos)

    if use_multithreading:
        threads = []
        for v in videos:
            t = threading.Thread(target=process_video, args=(v, test_mode, status))
            threads.append(t)
            t.start()

            if len(threads) >= max_threads:
                for t in threads:
                    t.join()
                threads = []

        for t in threads:
            t.join()

    else:
        for v in videos:
            process_video(v, test_mode, status)
