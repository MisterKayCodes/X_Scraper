from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio
import logging

from app.config import API_KEY
from app.services.profile_scraper import scrape_profile_media
from app.data.db_manager import set_setting, create_task, update_task_meta
from app.bot.queue_worker import harvester_queue
from fastapi.responses import FileResponse
from app.utils.downloader import download_with_ytdlp
from pathlib import Path
import os

app = FastAPI(title="X Scraper API", version="1.0.0")
logger = logging.getLogger("uvicorn.error")

# --- Security ---
def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or Missing API Key")
    return x_api_key

# --- Models ---
class ScrapeRequest(BaseModel):
    username: str
    limit: Optional[int] = 20
    destination_id: str  # Telegram Channel/Chat ID
    user_id: Optional[int] = 0  # Default system user

class SingleDownloadRequest(BaseModel):
    url: str

# --- Handlers ---
async def run_scrape_process(username: str, limit: int, destination_id: str, user_id: int):
    """
    Background process to find links and load them into the harvester queue.
    """
    try:
        # 1. Update Destination Setting for this user
        set_setting(user_id, "destination_channel_id", destination_id)
        
        # 2. Spawn Task in DB
        task_id = create_task(user_id, username)
        
        # 3. Scrape links (Resource Guarded by Phase 2 Semaphore)
        logger.info(f"[API] Starting scrape for @{username} (Limit: {limit})")
        links = await scrape_profile_media(username, user_id, limit)
        
        if not links:
            from app.data.db_task_layer import set_task_status
            set_task_status(task_id, 'STOPPED')
            logger.warning(f"[API] No links found for @{username}")
            return

        # 4. Load Conveyor Belt
        update_task_meta(task_id, len(links), 0) # 0 for msg_id as it's API triggered
        for link in links:
            await harvester_queue.put((link, user_id, task_id))
            
        logger.info(f"[API] Successfully queued {len(links)} items for @{username}")

    except Exception as e:
        logger.error(f"[🚨] API Scrape Process Failure: {e}")

# --- Endpoints ---
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "x-scraper-api"}

@app.get("/status")
async def status_report():
    """
    Returns a global health and status report for the Supervisor bot.
    """
    from app.data.db_manager import get_user_aggregated_stats, get_active_task
    from app.bot.queue_worker import harvester_queue
    
    stats = get_user_aggregated_stats(0)
    q_size = harvester_queue.qsize()
    active_task = get_active_task(0)
    
    return {
        "bot_name": "X Scraper",
        "status": "Running",
        "queue_size": q_size,
        "total_posts": stats.get('all_time_success', 0),
        "active_task": active_task['target_user'] if active_task else None
    }

@app.post("/scrape")
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks, _ = Depends(verify_api_key)):
    """
    Triggers a scraping task in the background.
    """
    background_tasks.add_task(
        run_scrape_process, 
        request.username, 
        request.limit, 
        request.destination_id, 
        request.user_id
    )
    return {
        "status": "success",
        "message": f"Scrape task for @{request.username} started in background.",
        "target": request.username,
        "destination": request.destination_id
    }

@app.post("/download")
async def download_single_link(request: SingleDownloadRequest, _ = Depends(verify_api_key)):
    """
    Downloads a single YouTube or X link and returns the media directly.
    """
    temp_dir = Path("app/downloads")
    temp_dir.mkdir(exist_ok=True)
    
    result = await download_with_ytdlp(request.url, temp_dir, check_size_first=False)
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Download failed'))
        
    file_path = result['file_path']
    return FileResponse(path=file_path, filename=file_path.name, media_type='application/octet-stream')
