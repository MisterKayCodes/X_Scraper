from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.bot.states import HarvestStates
from app.services.youtube_scraper import youtube_scraper
from app.data.db_manager import create_task, update_task_meta, get_setting, set_setting
from app.data.db_advanced import add_source_channel, add_telegram_channel, create_auto_check
from app.bot.queue_worker import harvester_queue
from app.bot.keyboards import get_dashboard_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

def get_yt_filter_keyboard(channel_url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎬 Videos Only", callback_data=f"yt_filter|videos|{channel_url}"),
            InlineKeyboardButton(text="⚡ Shorts Only", callback_data=f"yt_filter|shorts|{channel_url}")
        ],
        [InlineKeyboardButton(text="📦 Both (All Content)", callback_data=f"yt_filter|all|{channel_url}")]
    ])

def get_yt_limit_keyboard(url: str, filter_mode: str, total: int):
    """Quick-pick buttons for how many items to harvest."""
    options = [10, 20, 50]
    buttons = []
    row = []
    for n in options:
        if n <= total:
            row.append(InlineKeyboardButton(text=f"{n}", callback_data=f"yt_limit|{n}|{filter_mode}|{url}"))
    if row:
        buttons.append(row)
    # Always show "All" and "Custom"
    buttons.append([InlineKeyboardButton(text=f"📦 All ({total})", callback_data=f"yt_limit|{total}|{filter_mode}|{url}")])
    buttons.append([InlineKeyboardButton(text="✏️ Custom number...", callback_data=f"yt_limit|custom|{filter_mode}|{url}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_yt_save_keyboard(channel_url: str, filter_mode: str, limit: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes, Auto-Check", callback_data=f"yt_save|yes|{filter_mode}|{limit}|{channel_url}")],
        [InlineKeyboardButton(text="❌ No, One-Time Harvest", callback_data=f"yt_save|no|{filter_mode}|{limit}|{channel_url}")]
    ])

def get_yt_interval_keyboard(source_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Every 1 Hour", callback_data=f"yt_interval|60|{source_id}")],
        [InlineKeyboardButton(text="Every 6 Hours", callback_data=f"yt_interval|360|{source_id}")],
        [InlineKeyboardButton(text="Every 12 Hours", callback_data=f"yt_interval|720|{source_id}")],
        [InlineKeyboardButton(text="Every 24 Hours", callback_data=f"yt_interval|1440|{source_id}")]
    ])


@router.message(HarvestStates.awaiting_yt_url)
async def process_yt_url(message: types.Message, state: FSMContext):
    url = message.text.strip()
    if url.startswith("@"):
        url = f"https://youtube.com/{url}"
        
    await state.clear()
    
    await message.answer(
        f"🎯 Target Acquired: `{url}`\n\n"
        "What type of content do you want to harvest from this channel?",
        reply_markup=get_yt_filter_keyboard(url)
    )

@router.callback_query(F.data.startswith("yt_filter|"))
async def cb_yt_filter(callback: types.CallbackQuery):
    _, filter_mode, url = callback.data.split("|", 2)
    
    await callback.message.edit_text(
        f"🔍 Scanning **{url}**...\n\n"
        "_(Counting all videos & shorts — this may take 10–30 seconds for large channels)_"
    )
    await callback.answer()
    
    # Use get_channel_info() which has exact counts per tab — fast and accurate
    try:
        meta = await youtube_scraper.get_channel_info(url)
    except Exception:
        meta = {}
    
    video_count = meta.get("video_count", 0) or 0
    shorts_count = meta.get("shorts_count", 0) or 0
    total_all = video_count + shorts_count
    
    if filter_mode == "videos":
        total = video_count
    elif filter_mode == "shorts":
        total = shorts_count
    else:
        total = total_all
    
    if total == 0:
        await callback.message.edit_text(
            f"❌ No **{filter_mode}** content found on this channel.\n\nTry a different filter.",
            reply_markup=get_yt_filter_keyboard(url)
        )
        return
    
    summary = (
        f"📊 **Channel Overview**\n"
        f"──────────────────\n"
        f"🎬 Videos: **{video_count}**\n"
        f"⚡ Shorts: **{shorts_count}**\n"
        f"📦 Total: **{total_all}**\n"
        f"──────────────────\n"
        f"Your filter (**{filter_mode}**) matches **{total}** items.\n\n"
        f"How many do you want to harvest?"
    )
    
    await callback.message.edit_text(summary, reply_markup=get_yt_limit_keyboard(url, filter_mode, total))

@router.callback_query(F.data.startswith("yt_limit|"))
async def cb_yt_limit(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("|", 3)
    _, choice, filter_mode, url = parts
    
    if choice == "custom":
        await state.set_state(HarvestStates.awaiting_yt_limit)
        await state.update_data(yt_url=url, yt_filter=filter_mode)
        await callback.message.edit_text(
            "✏️ **Enter a custom number of videos to harvest:**\n"
            "_(Type a number and send it)_"
        )
        await callback.answer()
        return
    
    limit = int(choice)
    await callback.answer()
    await callback.message.edit_text(
        f"Selected: **{limit}** items\n\n"
        "💾 Want to save this channel for background Auto-Checking?",
        reply_markup=get_yt_save_keyboard(url, filter_mode, limit)
    )

@router.message(HarvestStates.awaiting_yt_limit)
async def process_yt_custom_limit(message: types.Message, state: FSMContext):
    try:
        limit = int(message.text.strip())
        if limit < 1:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Please enter a valid number (e.g. `15`).")
        return
    
    data = await state.get_data()
    url = data.get("yt_url")
    filter_mode = data.get("yt_filter")
    await state.clear()
    
    await message.answer(
        f"✅ Got it — harvesting **{limit}** items.\n\n"
        "💾 Want to save this channel for background Auto-Checking?",
        reply_markup=get_yt_save_keyboard(url, filter_mode, limit)
    )

@router.callback_query(F.data.startswith("yt_save|"))
async def cb_yt_save(callback: types.CallbackQuery):
    parts = callback.data.split("|", 4)
    _, choice, filter_mode, limit_str, url = parts
    user_id = callback.from_user.id
    limit = int(limit_str)
    
    if choice == "yes":
        meta = await youtube_scraper.get_channel_info(url)
        channel_name = meta.get('name', url.split('/')[-1]) if not meta.get('error') else url.split('/')[-1]
        
        source_id = await add_source_channel(
            user_id=user_id,
            platform="youtube",
            channel_url=url,
            channel_name=channel_name,
            collection_name=f"YT_{channel_name}"
        )
        set_setting(user_id, f"temp_yt_filter_{source_id}", filter_mode)
        set_setting(user_id, f"temp_yt_limit_{source_id}", str(limit))
        
        await callback.message.edit_text(
            f"✅ Channel saved as source.\n\n"
            "⏰ **How often should I check for new videos?**",
            reply_markup=get_yt_interval_keyboard(source_id)
        )
    else:
        await callback.message.edit_text("🚀 Starting one-time harvest...")
        await execute_yt_harvest(callback.message, user_id, url, filter_mode, limit)
    
    await callback.answer()

@router.callback_query(F.data.startswith("yt_interval|"))
async def cb_yt_interval(callback: types.CallbackQuery):
    _, interval_str, source_id_str = callback.data.split("|")
    interval = int(interval_str)
    source_id = int(source_id_str)
    user_id = callback.from_user.id
    
    target_channel = get_setting(user_id, "destination_channel_id")
    if not target_channel:
        await callback.message.edit_text("❌ No destination channel set in Settings. Please set it first.")
        return
        
    filter_mode = get_setting(user_id, f"temp_yt_filter_{source_id}") or "all"
    limit = int(get_setting(user_id, f"temp_yt_limit_{source_id}") or 20)
    
    tg_id = await add_telegram_channel(user_id, target_channel)
    
    await create_auto_check(
        user_id=user_id,
        source_channel_id=source_id,
        telegram_channel_id=tg_id,
        interval_minutes=interval,
        filter_mode=filter_mode
    )
    
    await callback.message.edit_text(
        f"✅ Auto-check configured for every {interval // 60 or interval} {'hour(s)' if interval >= 60 else 'minute(s)'}!\n"
        "Now starting initial harvest..."
    )
    
    from app.data.db_advanced import get_source_channel_by_id
    source = await get_source_channel_by_id(source_id)
    url = source['channel_url']
    
    await execute_yt_harvest(callback.message, user_id, url, filter_mode, limit)
    await callback.answer()

async def execute_yt_harvest(message: types.Message, user_id: int, url: str, filter_mode: str, limit: int = None):
    if limit is None:
        limit = int(get_setting(user_id, "harvest_limit") or 20)
    max_dur = int(get_setting(user_id, "max_duration_seconds") or 600)
    
    status_msg = await message.answer("🔍 **Scraping YouTube...**")
    
    # Create Task
    task_id = create_task(user_id, url)
    
    # Scrape with user-defined limit
    items = await youtube_scraper.scrape_channel(url, content_filter=filter_mode, limit=limit)
    
    if not items:
        from app.data.db_manager import set_task_status
        set_task_status(task_id, 'STOPPED')
        await status_msg.edit_text(f"❌ No videos found on {url}.")
        return
        
    queued_count = 0
    skipped_count = 0
    
    await status_msg.edit_text(f"⏳ **Applying duration filter (Max {max_dur // 60} min)...**")
    
    from app.data.db_manager import is_duplicate
    
    for item in items:
        # Check vault first
        tweet_id = item['content_url'].split("/")[-1]
        if is_duplicate(tweet_id, user_id):
            skipped_count += 1
            continue
            
        dur = item.get('duration')
        if dur is None:
            if "/shorts/" in item['content_url'] or "/short/" in item['content_url']:
                dur = 60
            else:
                dur = await youtube_scraper.get_video_duration(item['content_url'])
            
        if dur and dur > max_dur:
            skipped_count += 1
            continue
            
        queued_count += 1
        await harvester_queue.put((item['content_url'], user_id, task_id))
        
    update_task_meta(task_id, queued_count, status_msg.message_id)
    
    if queued_count == 0:
        from app.data.db_manager import set_task_status
        set_task_status(task_id, 'STOPPED')
        await status_msg.edit_text(
            f"❌ Found {skipped_count} videos, but ALL were skipped (exceeded {max_dur // 60} min limit)."
        )
        return
        
    await status_msg.edit_text(
        f"✅ **YouTube Harvest Queued:**\n"
        f"📥 Queued: **{queued_count}** videos\n"
        f"⏭️ Skipped: **{skipped_count}** (duration limit)\n\n"
        f"Dashboard engaged. Processing with jitter logic.",
        reply_markup=get_dashboard_keyboard(user_id)
    )
