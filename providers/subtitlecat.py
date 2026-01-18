import requests
from bs4 import BeautifulSoup
import time
import random
import re
import os

BASE_URL = "https://www.subtitlecat.com"


# ------------------------------------------------------------
# Utility: Cloudflare challenge detection
# ------------------------------------------------------------
def looks_like_cloudflare(html):
    if not html:
        return False
    text = html.lower()
    return (
        "just a moment" in text or
        "cloudflare" in text or
        "checking your browser" in text
    )


# ------------------------------------------------------------
# Safe GET with retry + backoff + Cloudflare detection
# ------------------------------------------------------------
def safe_get(url, log, retries=5, timeout=10):
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, timeout=timeout)
            html = r.text if hasattr(r, "text") else ""

            # Cloudflare challenge
            if looks_like_cloudflare(html):
                log.append(f"[SubCat] Cloudflare challenge detected (attempt {attempt})")
                time.sleep(random.uniform(1.2, 2.0))
                continue

            if r.status_code == 200:
                return r

            log.append(f"[SubCat] HTTP {r.status_code} (attempt {attempt})")

        except Exception as e:
            log.append(f"[SubCat] Request error: {e} (attempt {attempt})")

        # Backoff
        time.sleep(random.uniform(0.8, 1.6))

    log.append("[SubCat] Request failed after retries")
    return None


# ------------------------------------------------------------
# Search results page
# ------------------------------------------------------------
def find_best_result_href(search_url, code, log):
    log.append(f"[SubCat] Searching: {search_url}")

    r = safe_get(search_url, log)
    if not r:
        return None

    soup = BeautifulSoup(r.text, "lxml")
    table = soup.find("table", class_="table sub-table")
    if not table:
        log.append("[SubCat] No results table found")
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
        if code.lower() not in title.lower():
            continue

        cols = row.find_all("td")
        try:
            downloads = int(cols[-2].text.split()[0])
        except Exception:
            downloads = 0

        log.append(f"[SubCat] Candidate: '{title}' ({downloads} downloads)")

        if downloads > most_downloads:
            most_downloads = downloads
            best_href = a.get("href")

    if best_href:
        log.append(f"[SubCat] Best match → {best_href}")
    else:
        log.append("[SubCat] No matching titles found")

    return best_href


# ------------------------------------------------------------
# English subtitle link
# ------------------------------------------------------------
def get_english_download_href(page_url, log):
    log.append(f"[SubCat] Loading subtitle page: {page_url}")

    r = safe_get(page_url, log)
    if not r:
        return None

    soup = BeautifulSoup(r.text, "lxml")
    a = soup.find("a", id="download_en")

    if not a:
        log.append("[SubCat] No English subtitle link found")
        return None

    href = a.get("href")
    log.append(f"[SubCat] English subtitle link → {href}")
    return href


# ------------------------------------------------------------
# Main SubtitleCat logic (now hardened)
# ------------------------------------------------------------
def get_subtitle(jav_code, log):
    search_url = f"{BASE_URL}/index.php?search={jav_code}"

    # Retry search up to 3 times
    for attempt in range(1, 4):
        log.append(f"[SubCat] Search attempt {attempt}/3")
        page_href = find_best_result_href(search_url, jav_code, log)
        if page_href:
            break
        time.sleep(random.uniform(1.0, 2.0))

    if not page_href:
        log.append("[SubCat] Failed to find results after retries")
        return None

    if not page_href.startswith("/"):
        page_href = "/" + page_href

    page_url = BASE_URL + page_href

    # Retry English link up to 3 times
    for attempt in range(1, 4):
        log.append(f"[SubCat] English link attempt {attempt}/3")
        href = get_english_download_href(page_url, log)
        if href:
            break
        time.sleep(random.uniform(1.0, 2.0))

    if not href:
        log.append("[SubCat] Failed to get English subtitle link after retries")
        return None

    if not href.startswith("/"):
        href = "/" + href

    final_url = BASE_URL + href
    log.append(f"[SubCat] Downloading: {final_url}")

    # Retry download up to 3 times
    for attempt in range(1, 4):
        log.append(f"[SubCat] Download attempt {attempt}/3")
        r = safe_get(final_url, log)
        if r:
            log.append("[SubCat] Download successful")
            return {
                "content": r.content,
                "source": final_url,
                "provider": "subtitlecat"
            }
        time.sleep(random.uniform(1.0, 2.0))

    log.append("[SubCat] Failed to download subtitle after retries")
    return None
