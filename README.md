# X Media Scraper Toolkit 2026

A robust suite of Python scripts to scrape media (videos and photos) from X (Twitter). Built to bypass 2026 bot detection and handle bulk operations flawlessly.

## Core Features
1. **Single Link Downloader (`main.py`)**: 
   - Uses `vxtwitter` API to bypass blocks.
   - **Atomic Writes**: Downloads to a temporary `.part` file to prevent corruption if interrupted.
   - **Progress Bars**: Real-time terminal progress via `tqdm`.
   - **Header Mimicry**: Spoofs a real browser to pass firewall checks.
2. **Profile Scraper (`profile_scraper.py`)**: 
   - Gathers tweet links from a specific user profile and saves them to a text file in the `data/` folder.
3. **Bulk Downloader (`bulk_downloader.py`)**:
   - Takes a list of links (e.g., from the profile scraper) and downloads them automatically.
   - **Idempotency (Resume)**: Checks `data/processed_ids.json` and skips files it has already downloaded. You can stop and restart the script anytime.
   - **Rate Limiting**: Adds a random delay (2-5 seconds) between downloads to avoid bans.

## Setup
1. Run `setup.bat` to create a virtual environment and install dependencies (`tqdm`, `requests`, `loguru`, etc.).

## Usage
1. Run `run.bat`.
2. A menu will appear allowing you to choose between:
   - Single Link Download
   - Profile Scraping
   - Bulk Downloading
3. Extracted media will be saved in the `downloads/` folder.
4. Internal state tracking files are kept clean in the `data/` folder.
