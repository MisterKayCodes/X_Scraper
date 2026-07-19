"""
Sources Handlers — Add source, auto-check.
"""
import asyncio
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.bot.states import HarvestStates
from app.data.db_advanced import (
    add_source_channel, stop_auto_check, create_auto_check, 
    add_telegram_channel, get_active_auto_checks, delete_auto_check,
    get_all_auto_checks
)
from app.data.db_manager import get_task_by_id

router = Router(name="sources")

async def btn_addsource(message: types.Message, state: FSMContext):
    await state.set_state(HarvestStates.awaiting_new_source)
    await message.answer("📺 Send me the URL of the YouTube channel, X profile, or IG profile you want to add.")


async def btn_autocheck(message: types.Message, state: FSMContext):
    """
    Management Dashboard for Auto-Harvest.
    Lists all active watchdogs and provides controls.
    """
    checks = await get_all_auto_checks(message.from_user.id)
    
    if not checks:
        await message.answer(
            "🤖 **Auto-Harvest Watchdogs**\n\n"
            "You have no active background watchdogs.\n"
            "To enable one, start a scrape and click **🔄 Enable Auto-Check** on the dashboard."
        )
        return
        
    text = "🤖 **Auto-Harvest Watchdogs**\n\n"
    buttons = []
    
    for i, check in enumerate(checks):
        status = "🟢 Active" if check.get('is_active', 1) else "⏸️ Paused"
        platform = check.get('platform', 'unknown')
        url = check.get('channel_url', 'unknown')
        interval = check.get('interval_minutes', 0)
        
        # Display simplified names
        name = url.split('/')[-1] if '/' in url else url
        
        text += f"**{i+1}. {name} ({platform})**\n"
        text += f"Status: {status}\n"
        text += f"Interval: Every {interval} minutes\n\n"
        
        # Add a row of buttons for this check
        if check.get('is_active', 1):
            buttons.append([
                InlineKeyboardButton(text=f"⏸️ Pause #{i+1}", callback_data=f"autocheck_pause:{check['id']}"),
                InlineKeyboardButton(text=f"🗑️ Delete #{i+1}", callback_data=f"autocheck_del:{check['id']}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text=f"▶️ Resume #{i+1}", callback_data=f"autocheck_resume:{check['id']}"),
                InlineKeyboardButton(text=f"🗑️ Delete #{i+1}", callback_data=f"autocheck_del:{check['id']}")
            ])
            
    await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("autocheck_pause:"))
async def cb_autocheck_pause(callback: types.CallbackQuery):
    check_id = int(callback.data.split(":")[1])
    await stop_auto_check(check_id) # Set is_active = 0
    await callback.message.edit_text(callback.message.text + f"\n\n✅ Watchdog paused.")

@router.callback_query(F.data.startswith("autocheck_resume:"))
async def cb_autocheck_resume(callback: types.CallbackQuery):
    check_id = int(callback.data.split(":")[1])
    # Need an enable function, for now we will just delete and tell them to re-add, or implement resume later.
    # We can just update the row to is_active = 1
    import sqlite3
    from app.data.db_manager import db_path
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE auto_check SET is_active = 1 WHERE id = ?", (check_id,))
    conn.commit()
    conn.close()
    await callback.message.edit_text(callback.message.text + f"\n\n▶️ Watchdog resumed.")

@router.callback_query(F.data.startswith("autocheck_del:"))
async def cb_autocheck_del(callback: types.CallbackQuery):
    check_id = int(callback.data.split(":")[1])
    await delete_auto_check(check_id)
    await callback.message.edit_text(callback.message.text + f"\n\n🗑️ Watchdog deleted.")


# ─── Setup Auto-Check from Dashboard ───────────────────────────
@router.callback_query(F.data.startswith("setup_autocheck:"))
async def cb_setup_autocheck(callback: types.CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    task = get_task_by_id(task_id)
    
    if not task:
        await callback.answer("Task not found.", show_alert=True)
        return
        
    username = task['target_username']
    
    # Show interval picker
    buttons = [
        [InlineKeyboardButton(text="1 Hour", callback_data=f"autocheck_set:60:{task_id}")],
        [InlineKeyboardButton(text="6 Hours", callback_data=f"autocheck_set:360:{task_id}")],
        [InlineKeyboardButton(text="12 Hours", callback_data=f"autocheck_set:720:{task_id}")],
        [InlineKeyboardButton(text="24 Hours", callback_data=f"autocheck_set:1440:{task_id}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="close_menu")]
    ]
    
    await callback.message.edit_text(
        f"🔄 **Enable Auto-Check for** `{username}`\n\n"
        "How often should the watchdog scan this profile for new content in the background?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("autocheck_set:"))
async def cb_autocheck_set(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    interval_mins = int(parts[1])
    task_id = int(parts[2])
    
    task = get_task_by_id(task_id)
    if not task:
        return
        
    username = task['target_username']
    user_id = callback.from_user.id
    
    # We need to map the task's username to a source_channel
    # If the source doesn't exist, we create it.
    platform = "twitter" # We can deduce this from the task or just assume twitter for now
    url = f"https://x.com/{username.replace('@', '')}"
    
    source_id = await add_source_channel(
        user_id=user_id,
        platform=platform,
        channel_url=url,
        channel_name=username,
        collection_name=f"auto_{username}"
    )
    
    from app.data.db_manager import get_setting
    target_channel = get_setting(user_id, "destination_channel_id")
    
    if not target_channel:
        await callback.message.edit_text("❌ Please configure a destination channel in Settings first!")
        return
        
    tg_id = await add_telegram_channel(user_id, target_channel)
    
    await create_auto_check(
        user_id=user_id,
        source_channel_id=source_id,
        telegram_channel_id=tg_id,
        interval_minutes=interval_mins,
        filter_mode=task.get('media_filter', 'any')
    )
    
    hours = interval_mins // 60
    await callback.message.edit_text(
        f"✅ **Auto-Check Enabled!**\n\n"
        f"Watchdog will scan `{username}` every {hours} hour(s) and automatically post new content to your channel."
    )


@router.message(HarvestStates.awaiting_new_source)
async def process_new_source(message: types.Message, state: FSMContext):
    url = message.text.strip()
    platform = "unknown"
    if "youtube.com" in url or "youtu.be" in url:
        platform = "youtube"
    elif "twitter.com" in url or "x.com" in url:
        platform = "twitter"
    elif "instagram.com" in url:
        platform = "instagram"
        
    source_id = await add_source_channel(
        user_id=message.from_user.id,
        platform=platform,
        channel_url=url,
        channel_name=url.split('/')[-1],
        collection_name=f"{platform}_auto"
    )
    await state.clear()
    if source_id:
        await message.answer(f"✅ Added {platform} source! ID: {source_id}")
    else:
        await message.answer("❌ Failed to add source (might already exist).")