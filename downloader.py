import os
import time
import threading
import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.subtitlecat.com"
NET_SEM = threading.Semaphore(3)
SUB_CACHE = {}


# ------------------------------------------------------------
# JAV CODE EXTRACTION (kept from your improved version)
# ------------------------------------------------------------
def extract_jav_code(filename):
    """
    Extract JAV codes from messy filenames.
    """

    # Try bracketed first: [ABW-255]
    m = re.search(r"\[([A-Za-z]{2,10}[-_]\d{2,5}[A-Za-z]?)\]", filename)
    if m:
        return m.group(1)

    # General JAV code pattern
    matches = re.findall(r"[A-Za-z]{2,10}[-_]\d{2,5}[A-Za-z]?", filename)
    if matches:
        return matches[-1]

    return None


# ------------------------------------------------------------
# SAFE GET (critical fix: status_code)
# ------------------------------------------------------------
def safe_get(url, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:   # FIXED
                return r
        except Exception:
            pass
        time.sleep(1)
    return None


# ------------------------------------------------------------
# ORIGINAL MATCHING LOGIC (faithfully restored)
# ------------------------------------------------------------
def find_best_result_href(search_url, code):
    """
    Recreates original behavior:
    - simple substring match on <a>.text
    - pick highest download count
    - no normalization
    - no href matching
    """

    r = safe_get(search_url)
    if not r:
        return None

    soup = BeautifulSoup(r.text, "lxml")
    table = soup.find("table", class_="table sub-table")
    if not table:
        return None

    rows = table.find("tbody").find_all("tr")

    best_href = None
    most_downloads = 0

    for i, row in enumerate(rows):
        if i > 20:
            break

        a = row.find("a")
        if not a:
            continue

        title = a.text.strip()

        # ORIGINAL BEHAVIOR: simple substring match
        if code.lower() not in title.lower():
            continue

        cols = row.find_all("td")
        try:
            downloads = int(cols[-2].text.split()[0])
        except Exception:
            downloads = 0

        if downloads > most_downloads:
            most_downloads = downloads
            best_href = a.get("href")

    return best_href


# ------------------------------------------------------------
# ORIGINAL ENGLISH SUBTITLE LINK LOGIC
# ------------------------------------------------------------
def get_english_download_href(page_url):
    r = safe_get(page_url)
    if not r:
        return None

    soup = BeautifulSoup(r.text, "lxml")
    a = soup.find("a", id="download_en")
    if not a:
        return None

    return a.get("href")


# ------------------------------------------------------------
# MAIN SUBTITLECAT SCRAPER (faithful to original)
# ------------------------------------------------------------
def download_subtitle_from_subtitlecat(code):
    """
    Fully restored original behavior, with modern fixes.
    Returns a dict with bytes, title, and source URL.
    """

    if code in SUB_CACHE:
        logger.info(f"[SubtitleCat] Cache hit for {code}")
        return SUB_CACHE[code]

    with NET_SEM:
        search_url = f"{BASE_URL}/index.php?search={code}"
        logger.info(f"[SubtitleCat] Searching: {search_url}")

        # 1. Find best result page
        attempts = 0
        page_href = None

        while page_href is None and attempts < 6:
            page_href = find_best_result_href(search_url, code)
            if not page_href:
                attempts += 1
                time.sleep(1)

        if not page_href:
            logger.warning(f"[SubtitleCat] No matching subtitle for {code}")
            return None

        if not page_href.startswith("/"):
            page_href = "/" + page_href

        page_url = BASE_URL + page_href
        logger.info(f"[SubtitleCat] Best result page: {page_url}")

        # 2. Get English subtitle download link
        href = get_english_download_href(page_url)
        if not href:
            logger.warning(f"[SubtitleCat] No English subtitle link for {code}")
            return None

        if not href.startswith("/"):
            href = "/" + href

        final_url = BASE_URL + href
        logger.info(f"[SubtitleCat] Downloading: {final_url}")

        # 3. Download subtitle
        r = safe_get(final_url)
        if not r:
            logger.warning(f"[SubtitleCat] Failed to download subtitle for {code}")
            return None

        # Build metadata result
        result = {
            "bytes": r.content,
            "title": os.path.basename(page_href),
            "source": final_url
        }

        SUB_CACHE[code] = result
        return result

# ------------------------------------------------------------
# VIDEO SCANNING
# ------------------------------------------------------------
def scan_videos(root_dir, include_existing=False):
    results = []

    for root, dirs, files in os.walk(root_dir):
        for f in files:
            if f.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
                full = os.path.join(root, f)
                code = extract_jav_code(f)

                base, _ = os.path.splitext(full)
                has_sub = (
                    os.path.exists(base + ".srt") or
                    os.path.exists(base + ".en.srt")
                )


                results.append({
                    "file": full,
                    "code": code,
                    "has_sub": has_sub
                })

    return results


# ------------------------------------------------------------
# PROCESS SINGLE VIDEO
# ------------------------------------------------------------
def process_video(video, test_mode, status):
    if video.get("has_sub"):
        return

    status["processed"] += 1

    try:
        if test_mode:
            time.sleep(0.1)
            status["downloaded"] += 1
            return

        code = video.get("code")
        if not code:
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

    except Exception:
        status["failed"] += 1


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
        }

    videos = scan_videos(root_dir, include_existing=include_existing)

    if not include_existing:
        videos = [v for v in videos if not v["has_sub"]]

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

    return status
