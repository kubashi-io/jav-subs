import os
import time
import threading
import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.subtitlecat.com"

# Limit concurrent network calls to avoid rate limiting
NET_SEM = threading.Semaphore(3)

# Cache to avoid re-downloading the same code multiple times
SUB_CACHE = {}


# ------------------------------------------------------------
# JAV CODE EXTRACTION (FINAL, CORRECT VERSION)
# ------------------------------------------------------------
def extract_jav_code(filename):
    """
    Extract JAV codes from messy filenames.
    Correctly handles:
    - 2022-07-08 - Meguri Minoshima - ABW-255.mp4
    - hhd800.com@FJIN-098.mp4
    - [IPX-123].mp4
    - IPX_123A.mp4
    - SSIS-001-C.mp4
    """

    # 1. Try bracketed first: [ABW-255]
    m = re.search(r"\[([A-Za-z]{2,10}[-_]\d{2,5}[A-Za-z]?)\]", filename)
    if m:
        return m.group(1)

    # 2. General JAV code pattern (letters only prefix)
    matches = re.findall(r"[A-Za-z]{2,10}[-_]\d{2,5}[A-Za-z]?", filename)

    if matches:
        # Return the LAST match — JAV codes are usually at the end
        return matches[-1]

    return None


# ------------------------------------------------------------
# SAFE NETWORK WRAPPER
# ------------------------------------------------------------
def safe_get(url, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:  # <-- fixed here
                return r
        except Exception:
            pass
        time.sleep(1)
    return None


# ------------------------------------------------------------
# SUBTITLECAT SCRAPER
# ------------------------------------------------------------
def download_subtitle_from_subtitlecat(code):
    """
    Downloads English subtitles for a JAV code from SubtitleCat.
    Returns bytes or None.
    """

    # Cache hit
    if code in SUB_CACHE:
        logger.info(f"[SubtitleCat] Cache hit for {code}")
        return SUB_CACHE[code]

    with NET_SEM:  # limit concurrent requests
        logger.info(f"[SubtitleCat] Searching for: {code}")

        search_url = f"{BASE_URL}/index.php?search={code}"
        r = safe_get(search_url)
        if not r:
            logger.warning(f"[SubtitleCat] Search failed for {code}")
            return None

        soup = BeautifulSoup(r.text, "lxml")
        table = soup.find("table", class_="table sub-table")
        if not table:
            logger.warning(f"[SubtitleCat] No results table for {code}")
            return None

        rows = table.find("tbody").find_all("tr")
        best_href = None
        most_downloads = 0

        def normalize(s):
            return re.sub(r"[-_ .]", "", s).lower()

        norm_code = normalize(code)
        prefix = re.match(r"[A-Za-z]+", code).group(0).lower()

        for row in rows[:20]:
            a = row.find("a")
            if not a:
                continue

            title = a.text.strip()
            href = a.get("href", "")

            norm_title = normalize(title)
            norm_href = normalize(href)

            # 1. Exact code match
            exact = norm_code in norm_title or norm_code in norm_href

            # 2. Prefix match (fallback)
            prefix_match = prefix in norm_title or prefix in norm_href

            if not exact and not prefix_match:
                continue

            cols = row.find_all("td")
            try:
                downloads = int(cols[-2].text.split()[0])
            except Exception:
                downloads = 0

            if downloads > most_downloads:
                most_downloads = downloads
                best_href = href

        if not best_href:
            logger.warning(f"[SubtitleCat] No matching subtitle for {code}")
            return None

        final_url = f"{BASE_URL}{best_href}"
        logger.info(f"[SubtitleCat] Downloading from: {final_url}")

        r = safe_get(final_url)
        if not r:
            logger.warning(f"[SubtitleCat] Download failed for {code}")
            return None

        subtitle_bytes = r.content

        # Validate content
        if not subtitle_bytes or len(subtitle_bytes.strip()) < 10:
            logger.warning(f"[SubtitleCat] Empty or invalid subtitle for {code}")
            return None

        SUB_CACHE[code] = subtitle_bytes
        return subtitle_bytes


# ------------------------------------------------------------
# VIDEO SCANNING
# ------------------------------------------------------------
def scan_videos(root_dir, include_existing=False):
    logger.info(f"Scanning videos in: {root_dir}, include_existing={include_existing}")
    results = []

    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if f.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
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


# ------------------------------------------------------------
# PROCESS SINGLE VIDEO
# ------------------------------------------------------------
def process_video(video, test_mode, status):
    if video.get("has_sub"):
        logger.info(f"Skipping (subtitle exists): {video['file']}")
        return

    status["processed"] += 1
    logger.info(f"Processing: {video['file']} (test_mode={test_mode})")

    try:
        if test_mode:
            time.sleep(0.1)
            status["downloaded"] += 1
            logger.info(f"[TEST MODE] Marked as downloaded: {video['file']}")
            return

        code = video.get("code")
        if not code:
            logger.warning(f"No JAV code found for {video['file']}")
            status["failed"] += 1
            return

        subtitle_bytes = download_subtitle_from_subtitlecat(code)

        if not subtitle_bytes:
            status["failed"] += 1
            return

        srt_path = os.path.splitext(video["file"])[0] + ".srt"

        with open(srt_path, "wb") as f:
            f.write(subtitle_bytes)

        status["downloaded"] += 1
        logger.info(f"Saved subtitle: {srt_path}")

    except Exception as e:
        status["failed"] += 1
        logger.exception(f"Failed processing {video['file']}: {e}")


# ------------------------------------------------------------
# MAIN DOWNLOADER
# ------------------------------------------------------------
def run_downloader(
    root_dir,
    use_multithreading=True,
    max_threads=10,
    test_mode=False,
    include_existing=False,
    status=None
):
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
        logger.info("No videos to process after filtering.")
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
