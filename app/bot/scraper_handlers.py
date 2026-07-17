from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject
from app.services.x_scraper import fetch_x_metadata
from app.core.media_processor import parse_media_list, sanitize_filename, resolve_extension
from app.utils.downloader import download_file
from app.services.profile_scraper import scrape_profile_media
from app.bot.queue_worker import harvester_queue
from app.data.db_manager import create_task, update_task_meta
from app.bot.keyboards import get_dashboard_keyboard
from app.config import HEADERS, DOWNLOAD_DIR
from pathlib import Path

router = Router()

@router.message(F.text.contains("x.com") | F.text.contains("twitter.com"))
async def x_link_handler(message: types.Message):
    url = message.text.strip()
    status_msg = await message.answer("🔍 **Processing link...**")
    
    data, error = fetch_x_metadata(url)
    if error:
        await status_msg.edit_text(f"❌ **Error:** {error}")
        return

    caption = data.get("text", "x_media")
    safe_name = sanitize_filename(caption)
    media_list = parse_media_list(data)

    if not media_list:
        await status_msg.edit_text("ℹ️ **No media found in this post.**")
        return

    await status_msg.edit_text(f"📥 **Downloading {len(media_list)} items...**")
    
    download_path = Path(DOWNLOAD_DIR)
    download_path.mkdir(exist_ok=True)

    for i, item in enumerate(media_list):
        m_url = item.get("url")
        m_type = item.get("type", "image")
        ext = resolve_extension(m_type, m_url)
        
        filename = f"{safe_name}_{i}.{ext}" if len(media_list) > 1 else f"{safe_name}.{ext}"
        final_path = download_path / filename

        if download_file(m_url, final_path, HEADERS, quiet=True):
            # Send to user
            file_input = types.FSInputFile(str(final_path))
            
            media_caption = f"{caption}\n\n🎥 Item {i+1}" if len(media_list) > 1 else caption
            
            try:
                if "video" in m_type:
                    # Rule 8: Boring, reliable local upload
                    await message.answer_video(file_input, caption=media_caption)
                else:
                    await message.answer_photo(file_input, caption=media_caption)

            except Exception as error:
                # Rule 10: Observability - Log the actual error for us to see in the terminal
                user_id = message.from_user.id if message.from_user else "Unknown"
                print(f"[🚨] Upload Crash for User {user_id}: {error}")
                
                error_msg = str(error).lower()
                if "too large" in error_msg or "entity too large" in error_msg:
                    await message.answer(
                        f"⚠️ **Telegram Limit Hit**\n"
                        f"Item {i+1} is over 50MB. Telegram doesn't allow bots to upload files this large. "
                        f"Try a lower quality link if available."
                    )
                else:
                    await message.answer(f"❌ **Upload Failed:** I encountered a technical glitch delivering this item.")

            finally:
                # Rule 16: Boy Scout Rule - Always clean up the temporary file!
                if final_path.exists():
                    final_path.unlink()
                    print(f"DEBUG: Cleaned up temporary file: {final_path}")

        else:
            await message.answer(f"⚠️ Failed to download item {i+1}")

    await status_msg.delete()


@router.message(Command("scrape"))
async def scrape_handler(message: types.Message, command: CommandObject):
    """
    Usage: /scrape @username [limit]
    """
    args = command.args
    if not args:
        await message.answer("⚠️ **Usage:** `/scrape @username [limit]`\nExample: `/scrape @MisterKayCodes 20`")
        return

    parts = args.split()
    username = parts[0]
    limit = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 20
    
    status_msg = await message.answer(f"🔍 **Radar Engaged:** Harvesting last {limit} media from {username}...")
    
    # 1. Spawn Task
    task_id = create_task(message.from_user.id, username)
    
    # 2. Scrape links using Headless Radar
    async def update_status(text: str):
        try:
            await status_msg.edit_text(text)
        except Exception:
            pass
            
    links = await scrape_profile_media(username, message.from_user.id, limit, status_callback=update_status)
    
    if not links:
        from app.data.db_manager import set_task_status
        set_task_status(task_id, 'STOPPED')
        await status_msg.edit_text(f"❌ **Radar Failure:** No new media found for {username}.")
        return
        
    # 3. Load Conveyor Belt
    update_task_meta(task_id, len(links), status_msg.message_id)
    for link in links:
        await harvester_queue.put((link, message.from_user.id, task_id))
        
    await status_msg.edit_text(
        f"✅ **Harvester Loaded for @{username}:**\n"
        f"Found {len(links)} new tracks.\n"
        f"Dashboard engaged. Processing with Jitter logic.",
        reply_markup=get_dashboard_keyboard(message.from_user.id)
    )
