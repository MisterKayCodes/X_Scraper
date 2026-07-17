# 🧠 Learning Ledger

## 2026-03-15: Initial Architecture Setup
- **Fix**: Migrating from a single-script scraper to a multi-file "Mister Assistant" architecture.
- **Why**: Scalability, separation of concerns, and alignment with the user's preferred development pattern.
- **Pattern**: `core` for logic, `services` for API, `bot` for UI.

## 2026-07-17: yt-dlp Remuxing & DB Layer Enforcement
- **Fix**: Refactored the DB layer (`db_manager.py`, `db_advanced.py`) from `app.services` to `app.data`. 
- **Why**: The architectural inspector forbids database connections in the `services` layer, as `services` is strictly reserved for the Internet/API logic. Moving it to `data` resolves the "Mutant" architectural violation.
- **Fix**: Switched from standard requests to `yt-dlp` with `merge_output_format: 'mp4'`.
- **Why**: Telegram requires specific metadata (moov atom at the front, proper codec) to generate thumbnails and show duration for uploaded videos. `yt-dlp` handles the download and remuxing simultaneously, fixing Telegram media display bugs.
