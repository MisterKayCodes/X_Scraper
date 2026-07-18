import asyncio
import random
import os
from pathlib import Path
from aiogram import Bot, types
from app.services.x_scraper import fetch_x_metadata
from app.services.ig_scraper import download_ig_media
from app.core.media_processor import parse_media_list, sanitize_filename, resolve_extension
from app.utils.downloader import download_file
from app.data.db_manager import (
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
        
        # Rule: Jitter (60 - 120 seconds) to mimic human behavior and avoid bans
        wait_time = random.uniform(60.0, 120.0)
        print(f"[CONVEYOR] User {user_id} | Processing {url}. Sleeping for {wait_time:.2f}s jitter...")
        try:
            if user_id and user_id > 0:
                await bot.send_message(user_id, f"⏳ Throttling: Waiting {wait_time:.0f}s before processing next item...")
        except:
            pass
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
                
            # Pre-flight Admin Check
            target_channel = get_setting(user_id, "destination_channel_id")
            if target_channel:
                try:
                    chat_member = await bot.get_chat_member(target_channel, bot.id)
                    if chat_member.status not in ["administrator", "creator"]:
                        if user_id and user_id > 0:
                            await bot.send_message(user_id, f"🚨 **Pre-flight Error**: I am not an admin in the target channel `{target_channel}`! Please promote me.")
                        log_processed_item(task_id, success=False)
                        harvester_queue.task_done()
                        continue
                except Exception as e:
                    if user_id and user_id > 0:
                        await bot.send_message(user_id, f"🚨 **Pre-flight Error**: Could not verify admin status in `{target_channel}`. Error: {e}")
                    log_processed_item(task_id, success=False)
                    harvester_queue.task_done()
                    continue

            if url.startswith("ig_"):
                # ==========================
                # INSTAGRAM PROCESSING LOGIC
                # ==========================
                shortcode = url.replace("ig_", "")
                
                # Setup specific temp directory for this post to avoid collisions
                download_path = Path(config.DOWNLOAD_DIR) / shortcode
                download_path.mkdir(parents=True, exist_ok=True)
                
                media_files, caption, error = await download_ig_media(shortcode, download_path)
                
                if error or not media_files:
                    print(f"[🚨] IG Conveyor Error for {url}: {error}")
                    log_processed_item(task_id, success=False)
                    continue
                    
                target_channel = get_setting(user_id, "destination_channel_id")
                if not target_channel:
                    log_processed_item(task_id, success=False)
                    print(f"[!] Warning: No destination_channel_id set. Task {task_id} failing.")
                    continue

                import html
                media_caption = html.escape(caption)[:1000] # Telegram caption limits
                total_size_kb = sum(f.stat().st_size for f in media_files) // 1024
                
                try:
                    if len(media_files) == 1:
                        # Single item
                        f = media_files[0]
                        file_input = types.FSInputFile(str(f))
                        if f.suffix.lower() == '.mp4':
                            await bot.send_video(target_channel, video=file_input, caption=media_caption, request_timeout=300)
                        else:
                            await bot.send_photo(target_channel, photo=file_input, caption=media_caption, request_timeout=60)
                    else:
                        # Carousel / Media Group
                        media_group = []
                        for idx, f in enumerate(media_files[:10]): # Telegram allows max 10 per group
                            file_input = types.FSInputFile(str(f))
                            if f.suffix.lower() == '.mp4':
                                media_group.append(types.InputMediaVideo(media=file_input, caption=media_caption if idx == 0 else ""))
                            else:
                                media_group.append(types.InputMediaPhoto(media=file_input, caption=media_caption if idx == 0 else ""))
                        
                        await bot.send_media_group(target_channel, media=media_group, request_timeout=300)
                        
                    log_processed_item(task_id, success=True, size_kb=total_size_kb)
                    print(f"[OK] Organic IG upload triggered for {tweet_id} ({total_size_kb}KB)")
                except Exception as upload_error:
                    print(f"[🚨] IG Upload Failure: {upload_error}")
                    log_processed_item(task_id, success=False)
                finally:
                    # Clean up
                    for f in media_files:
                        try:
                            if f.exists(): f.unlink()
                        except: pass
                    try:
                        download_path.rmdir()
                    except: pass
            
            elif "youtube.com" in url or "youtu.be" in url:
                # ==========================
                # YOUTUBE PROCESSING LOGIC
                # ==========================
                from app.utils.downloader import download_with_ytdlp

                target_channel = get_setting(user_id, "destination_channel_id")
                if not target_channel:
                    log_processed_item(task_id, success=False)
                    print(f"[!] Warning: No destination_channel_id set. Task {task_id} failing.")
                    harvester_queue.task_done()
                    continue

                download_path = Path(config.DOWNLOAD_DIR)
                download_path.mkdir(exist_ok=True)

                if user_id and user_id > 0:
                    try:
                        await bot.send_message(user_id, f"📥 Downloading YouTube video...\n`{url}`")
                    except:
                        pass

                result = await download_with_ytdlp(url, download_path, check_size_first=True)

                if not result.get("success"):
                    err = result.get("error", "Unknown error")
                    print(f"[🚨] YouTube download failed for {url}: {err}")
                    log_processed_item(task_id, success=False)
                    if user_id and user_id > 0:
                        try:
                            await bot.send_message(user_id, f"❌ **YouTube Download Failed:** {err}")
                        except:
                            pass
                    harvester_queue.task_done()
                    continue

                file_path = result["file_path"]
                title = result.get("title", "YouTube Video")
                size_kb = int(result.get("filesize_mb", 0) * 1024)

                import html as _html
                media_caption = _html.escape(title)[:1024]

                try:
                    file_input = types.FSInputFile(str(file_path))
                    await bot.send_video(
                        target_channel,
                        video=file_input,
                        caption=media_caption,
                        supports_streaming=True,
                        request_timeout=300
                    )
                    log_processed_item(task_id, success=True, size_kb=size_kb)
                    print(f"[OK] YouTube upload complete for {url} ({size_kb}KB)")
                except Exception as upload_error:
                    print(f"[🚨] YouTube Upload Failure: {upload_error}")
                    log_processed_item(task_id, success=False)
                    if user_id and user_id > 0:
                        try:
                            await bot.send_message(user_id, f"❌ **YouTube Upload Failed:** {upload_error}")
                        except:
                            pass
                finally:
                    try:
                        if file_path.exists():
                            file_path.unlink()
                    except Exception as e:
                        print(f"[!] YouTube cleanup error: {e}")

            else:
                # ==========================
                # X (TWITTER) PROCESSING LOGIC
                # ==========================
                data, error = await asyncio.to_thread(fetch_x_metadata, url)
                caption = data.get("text", "x_media") if data else "x_media"
                safe_name = sanitize_filename(caption)
                
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
                    
                    filename = f"{safe_name}_{i}.{ext}" if len(media_list) > 1 else f"{safe_name}.{ext}"
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
