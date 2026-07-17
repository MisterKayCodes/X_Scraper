# 🤖 Mister Assistant - X Scraper

A powerful, multi-platform Telegram Bot and REST API for automated media scraping and posting. Supports **X (Twitter)**, **Instagram**, and **YouTube**. Built on the Mister Assistant architecture with strict layer separation, anti-ban throttling, and full lifecycle transparency.

---

## Architecture

This project strictly follows the **Mister Assistant Blueprint**:

| Layer | Path | Purpose |
| :--- | :--- | :--- |
| 🗣️ The Mouth | `app/bot/` | Telegram UI, commands, callbacks |
| 🧠 The Brain | `app/core/` | Pure logic — no internet, no DB |
| 🔌 The Wires | `app/services/` | Internet & API scraping only |
| 🗄️ The Memory | `app/data/` | Database access only |
| 🛠️ Utils | `app/utils/` | Reusable helpers and loggers |

---

## Core Features

### 📡 Multi-Platform Scraping
- **X (Twitter)**: Stealth browser scraping via Playwright
- **Instagram**: Session-based scraping via Instaloader
- **YouTube**: Fast channel/shorts/videos discovery via `yt-dlp` (extract-flat mode)

### 🎞️ Smart Downloading & Remuxing
- All video downloads use `yt-dlp` with `merge_output_format: mp4`
- This remuxes the container with proper metadata so **Telegram correctly shows thumbnails and video duration**
- **50MB Pre-flight Check** — skips oversized videos *before* downloading

### ⏰ Customizable Auto-Check Scheduler
- Add multiple source channels (YouTube, X, IG) per user
- Set custom check intervals (e.g., every 60 minutes) per source
- New content is automatically scraped and queued for posting

### 🛡️ Safety & Anti-Ban
- **Pre-flight Admin Check**: Bot verifies it has admin rights in the target Telegram channel before posting
- **Throttling**: Random 60–120 second jitter between downloads
- **Transparency**: Bot sends live status updates to the user during operations

### 🌐 FastAPI Layer (Always Open)
- `GET /health` — Health check
- `POST /scrape` — Trigger a background profile scrape
- `POST /download` — Download a single YouTube or X link; returns the file directly

---

## Telegram Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Open the main dashboard |
| `/stats` | View your global scraping statistics |
| `/settings` | Manage destination channel and targets |
| `/addsource` | Add a new YouTube / X / IG channel to monitor |
| `/autocheck` | Set up an automated interval check for a source |

---

## Setup
1. Run `setup.bat` to create a virtual environment and install all dependencies.
2. Copy `.env.example` to `.env` and fill in your bot token, API key, etc.
3. Run `run.bat` to start the bot with hot-reload enabled.
