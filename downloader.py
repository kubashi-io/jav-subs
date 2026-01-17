import os
import time
import threading
import re


def extract_jav_code(filename):
    """
    Extract a simple JAV-style code like ABC-123 from the filename.
    """
    match = re.search(r"[A-Za-z]{2,5}-\d{2,5}", filename)
    return match.group(0) if match else None


def scan_videos(root_dir, include_existing=False):
    """
    Walk the root_dir and return a list of video metadata:
    {
        "file": full_path,
        "code": extracted_code or None,
        "has_sub": True/False
    }

    include_existing:
        - False = return all files, but downloader will skip existing subs
        - True  = return all files AND downloader will process all
    """
    results = []

    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if f.lower().endswith((".mp4", ".mkv", ".avi")):
                full = os.path.join(root, f)
                code = extract_jav_code(f)

                base, _ = os.path.splitext(full)
                has_sub = os.path.exists(base + ".srt")

                results.append({
                    "file": full,
                    "code": code,
                    "has_sub": has_sub
                })

    return results


def process_video(video, test_mode, status):
    """
    Process a single video:
    - Skip if it already has subtitles (unless include_existing was enabled earlier)
    - In test mode, simulate success without writing files
    - Otherwise, perform the real download (placeholder here)
    """

    # Safety: skip if subtitles already exist
    if video.get("has_sub"):
        return

    status["processed"] += 1

    if test_mode:
        # Simulate a successful "download"
        status["downloaded"] += 1
        return

    # TODO: replace this with real subtitle download logic
    # Simulate network / processing delay
    time.sleep(1)

    status["downloaded"] += 1


def run_downloader(
    root_dir,
    use_multithreading=True,
    max_threads=10,
    test_mode=False,
    include_existing=False,
    status=None
):
    """
    Main entry point for the downloader.
    - Scans videos
    - Filters out those that already have subtitles (unless include_existing=True)
    - Processes remaining videos (optionally multithreaded)
    - Updates the shared status dict
    """

    if status is None:
        status = {
            "total": 0,
            "processed": 0,
            "downloaded": 0,
            "failed": 0,
            "running": False,
            "start_time": None
        }

    # Scan all videos
    videos = scan_videos(root_dir, include_existing=include_existing)

    # Filter out videos that already have subtitles unless toggle is ON
    if not include_existing:
        videos = [v for v in videos if not v["has_sub"]]

    status["total"] = len(videos)

    if not videos:
        return

    # Multithreaded mode
    if use_multithreading:
        threads = []

        for v in videos:
            t = threading.Thread(target=process_video, args=(v, test_mode, status))
            threads.append(t)
            t.start()

            # Limit concurrency
            if len(threads) >= max_threads:
                for t in threads:
                    t.join()
                threads = []

        # Join remaining threads
        for t in threads:
            t.join()

    # Single-threaded mode
    else:
        for v in videos:
            process_video(v, test_mode, status)
