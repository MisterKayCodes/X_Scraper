from aiogram import Router, types, F
from aiogram.filters import Command
from app.services.x_scraper import fetch_x_metadata
from app.core.media_processor import parse_media_list, sanitize_filename, resolve_extension
from app.utils.downloader import download_file
from app.config import HEADERS, DOWNLOAD_DIR
from pathlib import Path
import os

router = Router()

@router.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("👋 **Welcome to X Media Scraper!**\n\nSend me an X (Twitter) post link, and I'll extract the media for you.")

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
            
            if "video" in m_type:
                await message.answer_video(file_input, caption=media_caption)
            else:
                await message.answer_photo(file_input, caption=media_caption)
        else:
            await message.answer(f"⚠️ Failed to download item {i+1}")

    await status_msg.delete()
