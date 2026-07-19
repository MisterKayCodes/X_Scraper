import asyncio
from datetime import datetime, timedelta
import logging
from app.data.db_advanced import (
    get_active_auto_checks, update_auto_check, get_source_channel_by_id,
    get_existing_content_ids, add_scraped_content
)
from app.services.youtube_scraper import youtube_scraper
from app.services.profile_scraper import scrape_profile_media
from app.bot.queue_worker import harvester_queue
from app.data.db_manager import create_task, update_task_meta, get_setting

logger = logging.getLogger("scheduler")

async def run_auto_check_loop():
    logger.info("[SCHEDULER] Auto-check loop started.")
    while True:
        try:
            checks = await get_active_auto_checks()
            for check in checks:
                source_id = check['source_channel_id']
                platform = check['platform']
                url = check['channel_url']
                user_id = check['user_id']
                tg_channel = check['telegram_channel_id']
                
                # Mark as running
                await update_auto_check(check['id'], is_running=1)
                
                try:
                    logger.info(f"[SCHEDULER] Running check for {platform} - {url}")
                    existing_ids = await get_existing_content_ids(source_id)
                    new_items = []
                    
                    if platform == 'youtube':
                        new_items = await youtube_scraper.scrape_channel(
                            url, existing_ids=existing_ids, 
                            content_filter=check['filter_mode'], limit=10
                        )
                    elif platform == 'twitter':
                        username = url.split('/')[-1]
                        links = await scrape_profile_media(username, user_id, 10)
                        for link in links:
                            tweet_id = link.split('/')[-1]
                            if tweet_id not in existing_ids:
                                new_items.append({
                                    'content_id': tweet_id,
                                    'content_url': link,
                                    'content_type': 'video'
                                })
                    
                    # Process new items
                    if new_items:
                        logger.info(f"[SCHEDULER] Found {len(new_items)} new items for {url}")
                        task_id = create_task(user_id, url)
                        
                        max_dur = int(get_setting(user_id, "max_duration_seconds") or 600)
                        valid_items = []
                        
                        for item in new_items:
                            if platform == 'youtube':
                                dur = item.get('duration')
                                if dur is None:
                                    dur = await youtube_scraper.get_video_duration(item['content_url'])
                                if dur and dur > max_dur:
                                    continue # Skip
                            valid_items.append(item)
                            
                        update_task_meta(task_id, len(valid_items), 0)
                        
                        for item in valid_items:
                            await add_scraped_content(
                                source_channel_id=source_id,
                                platform=platform,
                                content_url=item['content_url'],
                                content_id=item['content_id'],
                                title=item.get('title'),
                                content_type=item.get('content_type')
                            )
                            # Push to harvester queue
                            await harvester_queue.put((item['content_url'], user_id, task_id))
                    
                    # Update check status
                    next_run = datetime.now() + timedelta(minutes=check['interval_minutes'])
                    await update_auto_check(
                        check['id'], 
                        is_running=0, 
                        last_check=datetime.now().isoformat(),
                        next_check=next_run.isoformat(),
                        last_new_count=len(new_items)
                    )
                    
                except Exception as e:
                    logger.error(f"[SCHEDULER] Error processing {url}: {e}")
                    # Revert running state
                    await update_auto_check(check['id'], is_running=0)
                    
        except Exception as e:
            logger.error(f"[SCHEDULER] Loop error: {e}")
            
        await asyncio.sleep(60) # Wake up every minute to check schedule
