import asyncio
import random
import os
from pathlib import Path
from aiogram import Bot, types
from app.services.x_scraper import fetch_x_metadata
from app.core.media_processor import parse_media_list, sanitize_filename, resolve_extension
from app.utils.downloader import download_file
from app.services.db_manager import (
    get_setting, mark_as_seen, 
    get_task_by_id, log_processed_item, set_task_status
)
from app.bot.keyboards import get_dashboard_keyboard
from app import config
import time

# Global Queue for Harvester
harvester_queue = asyncio.Queue()

async def queue_consumer(bot: Bot):
    """
    Background worker that processes the harvester_queue with Task-Centric logic.
    """
    print("[CONVEYOR] Background worker started.")
    
    while True:
        # Wait for (url, user_id, task_id) from the queue
        item = await harvester_queue.get()
        if not isinstance(item, tuple) or len(item) < 3:
            harvester_queue.task_done()
            continue
            
        url, user_id, task_id = item
        tweet_id = url.split("/")[-1]
        
        # Rule: Jitter (12 - 27 seconds) to mimic human behavior
        wait_time = random.uniform(12.0, 27.0)
        print(f"[CONVEYOR] User {user_id} | Processing {url}. Sleeping for {wait_time:.2f}s jitter...")
        await asyncio.sleep(wait_time)
        
        try:
            # 1. Fetch Task Context
            task = get_task_by_id(task_id)
            if not task:
                harvester_queue.task_done()
                continue
            
            # 🛑 BREAK: Check for user-requested stop or pause
            while task['status'] == 'PAUSED':
                await asyncio.sleep(5)
                task = get_task_by_id(task_id) # Refresh
                if not task or task['status'] == 'STOPPED':
                    break
            
            if not task or task['status'] == 'STOPPED':
                print(f"[🛑] Task {task_id} was STOPPED. Skipping item.")
                harvester_queue.task_done()
                continue

            # 1. Fetch Metadata
            data, error = await asyncio.to_thread(fetch_x_metadata, url)
            caption = data.get("text", "x_media") if data else "x_media"
            safe_name = sanitize_filename(caption)
            
            # 2. Sync HUD with Enterprise Format + Active Download Tracker
            try:
                efficiency = (task['success_count'] / max(1, task['processed_count'])) * 100
                storage_mb = task['storage_kb'] / 1024
                remaining = task['total_items'] - task['processed_count']
                eta_m = (remaining * 20) // 60
                
                progress_text = (
                    f"📊 **Enterprise Stats Card**\n"
                    f"───────────────────\n"
                    f"🎯 **Target:** @{task['target_username'].replace('@', '')}\n"
                    f"⏳ **Status:** DOWNLOADING\n"
                    f"📥 **File:** `{safe_name[:25]}...`\n\n"
                    f"📈 **Efficiency:** {efficiency:.1f}%\n"
                    f"📦 **Posted:** {task['success_count']} / {task['total_items']}\n"
                    f"💾 **Storage Saved:** {storage_mb:.2f} MB\n"
                    f"⏱️ **ETA:** ~{int(eta_m)} mins remaining\n"
                    f"───────────────────"
                )
                # Rule: Only update HUD if it was triggered by a Bot message (msg_id > 0)
                if task['last_msg_id'] and task['last_msg_id'] > 0:
                    await bot.edit_message_text(
                        text=progress_text, 
                        chat_id=user_id, 
                        message_id=task['last_msg_id'],
                        reply_markup=get_dashboard_keyboard(user_id)
                    )
                else:
                    print(f"[CONVEYOR] {task['target_username']} | Progress: {task['success_count']} / {task['total_items']}")
            except Exception as HUD_error:
                print(f"[!] HUD Sync Warning: {HUD_error}")
            if error:
                print(f"[🚨] Conveyor Error for {url}: {error}")
                log_processed_item(task_id, success=False)
                continue
                
            media_list = parse_media_list(data)
            
            if not media_list:
                print(f"[CONVEYOR] No media found in {url}")
                log_processed_item(task_id, success=False)
                continue
            
            download_path = Path(config.DOWNLOAD_DIR)
            download_path.mkdir(exist_ok=True)
            
            # Process each media item in the tweet
            for i, item in enumerate(media_list):
                m_url = item.get("url")
                m_type = item.get("type", "image")
                ext = resolve_extension(m_type, m_url)
                
                filename = f"{safe_name}_{i}.{ext}" if len(media_list) > 1 else f"{safe_name}.ext"
                final_path = download_path / filename
                
                # Rule: Atomic 128KB Reliable Download - Wrapped in to_thread!
                download_success = await asyncio.to_thread(
                    download_file, m_url, final_path, config.HEADERS, quiet=False
                )
                if download_success:
                    # Rule 8: Organic Upload to Destination Channel
                    target_channel = get_setting(user_id, "destination_channel_id")
                    if target_channel:
                        file_input = types.FSInputFile(str(final_path))
                        import html
                        media_caption = html.escape(caption)
                        
                        try:
                            file_size_kb = final_path.stat().st_size // 1024
                            if "video" in m_type:
                                await bot.send_video(target_channel, video=file_input, caption=media_caption, request_timeout=300)
                            else:
                                await bot.send_photo(target_channel, photo=file_input, caption=media_caption, request_timeout=60)
                            
                            log_processed_item(task_id, success=True, size_kb=file_size_kb)
                            print(f"[OK] Organic upload triggered for {tweet_id} ({file_size_kb}KB)")
                        except Exception as upload_error:
                            print(f"[🚨] Conveyor Upload Failure with caption: {upload_error}. Retrying without caption...")
                            try:
                                # Fallback: No caption
                                file_input = types.FSInputFile(str(final_path)) # Re-init stream just in case
                                if "video" in m_type:
                                    await bot.send_video(target_channel, video=file_input, request_timeout=300)
                                else:
                                    await bot.send_photo(target_channel, photo=file_input, request_timeout=60)
                                log_processed_item(task_id, success=True, size_kb=file_size_kb)
                                print(f"[OK] Fallback upload triggered for {tweet_id} (No Caption)")
                            except Exception as fallback_error:
                                log_processed_item(task_id, success=False)
                                print(f"[🚨] Absolute Upload Failure for {tweet_id}: {fallback_error}")
                        finally:
                            try:
                                if final_path.exists():
                                    final_path.unlink()
                            except Exception as e:
                                print(f"[!] WinError {e} - Skipping cleanup for {final_path.name}")
                    else:
                        log_processed_item(task_id, success=False)
                        print(f"[!] Warning: No destination_channel_id set. Task {task_id} failing items.")
                                
                else:
                    log_processed_item(task_id, success=False)
                    print(f"[!] Failed to download item for {url}")
            
            # Mark as processed in the Vault
            mark_as_seen(tweet_id, user_id, task['target_username'])
            
            # Final Check: If task is done
            updated_task = get_task_by_id(task_id)
            if updated_task and updated_task['processed_count'] >= updated_task['total_items']:
                set_task_status(task_id, 'COMPLETED')
                # Rule: Only notify user if user_id is valid (not 0/system)
                if user_id and user_id > 0:
                    try:
                        await bot.send_message(user_id, f"🎯 **Task Completed!** @{task['target_username']} harvest finished.")
                    except Exception:
                        pass
            
        except Exception as e:
            print(f"[🚨] Conveyor Loop Failure: {e}")
        finally:
            harvester_queue.task_done()
