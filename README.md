# JAV Subtitle Downloader
A  web application that scans a video directory, extracts JAV codes, downloads English subtitles from SubtitleCat, and saves them as .en.srt files.
Includes real‑time logs and progress tracking.

## Features
* Automatic JAV code detection
* SubtitleCat scraping with best‑match selection
* Saves subtitles as filename.en.srt
* Skips videos that already have subtitles
* Always‑visible, color‑coded logs
* Progress bar and status indicators


## Docker Compose

```
version: "3.9"

services:
  jav-subs:
    image: ghcr.io/caldwell-41/jav-subs:latest
    container_name: jav-subs
    restart: unless-stopped

    ports:
      - "16969:16969"

    environment:
      VIDEO_DIR: /videos

    volumes:
      - /path/to/your/videos:/videos

```

## Unraid

1. Add a new Docker container

2. Use the image:
```
ghcr.io/caldwell-41/jav-subs:latest
```
3. Map your video directory:
```
/mnt/user/yourvideos → /videos
```
4. Map port:
```
16969 → 16969
```
5. Apply and start

6. Visit:
```
http://your-unraid-ip:8000
```
