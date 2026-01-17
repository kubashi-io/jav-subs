import os
import time
import threading
import re
import logging

logger = logging.getLogger(__name__)


def extract_jav_code(filename):
    """
    Extract a JAV-style code like FJIN-098 from the filename.
    Handles prefixes like 'hhd800.com@FJIN-098'.
    """
    match = re.search(r"[A-Za-z0-9]{2,10}-\d{2,5}", filename)
    code = match.group(0) if match else None
    logger.debug(f"Extracted code from '{filename}': {code}")
    return code


def scan_videos(root_dir, include_existing=False):
    """
    Walk the root_dir and return a list of video metadata:
    {
        "file": full_path,
        "code": extracted_code or None,
        "has_sub": True/False
    }
    """
    logger.info(f"Scanning videos in: {root_dir}, include_existing={include_existing}")
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

    logger.info(f"Scan complete. Found {len(results)} video files.")
    return results


def process_video(video, test_mode, status):
    """
    Process a single video:
    - Skip if it already has subtitles (unless include_existing was handled earlier)
    - In test mode, simulate success without writing files
    - Otherwise, perform the real download (placeholder here)
    """
    if video.get("has_sub"):
        logger.info(f"Skipping (subtitle exists): {video['file']}")
        return

    status["processed"] += 1
    logger.info(f"Processing: {video['file']} (test_mode={test_mode})")

    try:
        if test_mode:
            # Simulate a successful "download"
            time.sleep(0.1)
            status["downloaded"] += 1
            logger.info(f"[TEST MODE] Marked as downloaded: {video['file']}")
            return

        # TODO: replace this with real subtitle download logic
        time.sleep(1)
        status["downloaded"] += 1
        logger.info(f"Downloaded subtitles for: {video['file']}")

    except Exception as e:
        status["failed"] += 1
        logger.exception(f"Failed processing {video['file']}: {e}")


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

    logger.info(
        f"run_downloader called with root_dir={root_dir}, "
        f"use_multithreading={use_multithreading}, max_threads={max_threads}, "
        f"test_mode={test_mode}, include_existing={include_existing}"
    )

    videos = scan_videos(root_dir, include_existing=include_existing)

    if not include_existing:
        before = len(videos)
        videos = [v for v in videos if not v["has_sub"]]
        logger.info(f"Filtered existing subtitles: {before} → {len(videos)} to process")

    status["total"] = len(videos)

    if not videos:
        logger.info("No videos to process after filtering. Exiting run_downloader.")
        return

    if use_multithreading:
        logger.info("Starting multithreaded processing")
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
        logger.info("Starting single-threaded processing")
        for v in videos:
            process_video(v, test_mode, status)

    logger.info(
        f"run_downloader finished. total={status['total']}, "
        f"processed={status['processed']}, downloaded={status['downloaded']}, "
        f"failed={status['failed']}"
    )
