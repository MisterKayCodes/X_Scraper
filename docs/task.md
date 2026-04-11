# Task: X Scraper to API Transformation

- [x] Phase 1: Environment & Core Setup
    - [x] Create task.md for tracking
    - [x] Update .env with API_KEY and API_PORT
    - [x] Update requirements.txt with fastapi and uvicorn
- [x] Phase 2: Resource Guard (VPS Protection)
    - [x] Implement global asyncio.Semaphore in profile_scraper.py
    - [x] Wrap browser launch logic with semaphore context
- [x] Phase 3: The API Backbone
    - [x] Update config.py with API settings
    - [x] Create api.py with FastAPI and X-API-KEY security
- [x] Phase 4: Connecting the Conveyor Belt
    - [x] Handle API tasks in queue_worker.py (skip HUD if msg_id=0)
    - [x] Add notification safety for system user_id
- [x] Phase 5: Entry Point Harmonization
    - [x] Integrate uvicorn server into main.py
    - [x] Use asyncio.gather to run Bot, API, and Worker together
    - [x] Move task/tracking docs to root folder
- [/] Phase 6: Multi-API Deployment Guide
