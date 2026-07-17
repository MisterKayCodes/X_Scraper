from aiogram import Router, types, F
from aiogram.filters import Command, CommandObject

from app.data.db_manager import (
    set_setting, get_setting, create_task, update_task_meta, get_user_aggregated_stats
)
from app.data.db_advanced import (
    add_source_channel, add_telegram_channel, create_auto_check, stop_auto_check, get_source_channel_by_id
)
from app.bot.keyboards import (
    get_settings_keyboard, get_verify_keyboard, 
    get_start_keyboard, get_dashboard_keyboard
)

from typing import Dict
from pathlib import Path
# Simple State Machine
user_states: Dict[int, str] = {}

router = Router()
from app.bot.scraper_handlers import router as scraper_router
router.include_router(scraper_router)

@router.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "🚀 **Mister Assistant: Command Center**\n"
        "Control your harvesting operations below.",
        reply_markup=get_dashboard_keyboard(message.from_user.id)
    )

@router.message(Command("dashboard"))
async def dashboard_handler(message: types.Message):
    await message.answer(
        "📊 **Active Dashboard**",
        reply_markup=get_dashboard_keyboard(message.from_user.id)
    )

@router.message(Command("stats"))
async def stats_handler(message: types.Message):
    stats = get_user_aggregated_stats(message.from_user.id)
    
    if stats['total_tasks'] == 0:
        await message.answer("📊 **Global Content Stats**\n\nYou haven't started any harvesting tasks yet!")
        return
        
    storage_mb = (stats['all_time_storage_kb'] or 0) / 1024
    success = stats['all_time_success'] or 0
    total = stats['all_time_items'] or 0
    efficiency = (success / max(1, total)) * 100
    
    stats_text = (
        f"📊 **Global Content Stats**\n"
        f"───────────────────\n"
        f"🚀 **Total Tasks Run:** {stats['total_tasks']}\n"
        f"📦 **Total Items Found:** {total}\n"
        f"✅ **Total Successfully Posted:** {success}\n"
        f"📈 **Lifetime Efficiency:** {efficiency:.1f}%\n"
        f"💾 **Total Storage Saved:** {storage_mb:.2f} MB\n"
        f"───────────────────"
    )
    
    await message.answer(stats_text)

@router.message(Command("addsource"))
async def addsource_handler(message: types.Message):
    user_states[message.from_user.id] = "awaiting_new_source"
    await message.answer("📺 Send me the URL of the YouTube channel, X profile, or IG profile you want to add.")

@router.message(Command("autocheck"))
async def autocheck_handler(message: types.Message):
    user_states[message.from_user.id] = "awaiting_autocheck_setup"
    await message.answer("⚙️ Send me the setup in this format: `source_id | target_channel_id | interval_minutes`\nExample: `1 | -100123456 | 60`\nOr send `stop | source_id` to stop auto-checking for a source.")

@router.message(Command("settings"))
async def settings_handler(message: types.Message):
    await message.answer("🛠️ **Mister Assistant Settings**\nManage your destination and targets below:", reply_markup=get_settings_keyboard())

@router.message()
async def state_handler(message: types.Message):
    """
    Handles text inputs based on the user's current state.
    Includes 'Magic Link' and 'Forward' detection for Channel IDs.
    """
    state = user_states.get(message.from_user.id)
    if not state:
        return # Standard message, ignore

    if state == "awaiting_channel_id":
        channel_id = None
        
        # 1. Check for Forwarded Message
        if message.forward_from_chat:
            channel_id = str(message.forward_from_chat.id)
            print(f"[MAGIC] Detected ID from Forward: {channel_id}")
            
        # 2. Check for Username or Link
        elif message.text:
            text = message.text.strip()
            if text.startswith("-100"):
                channel_id = text
            elif text.startswith("@") or "t.me/" in text:
                username = text.split("/")[-1].replace("@", "")
                try:
                    chat = await message.bot.get_chat(f"@{username}")
                    channel_id = str(chat.id)
                    print(f"[MAGIC] Resolved Username {username} to {channel_id}")
                except Exception as e:
                    await message.answer(f"❌ **Resolution Failed:** Could not find a channel named `{username}`. Make sure it's public or try a forwarded message.")
                    return

        if not channel_id:
            await message.answer("❌ Invalid input. Please **forward a message** from your channel or send a `@username`.")
            return

        set_setting(message.from_user.id, "destination_channel_id", channel_id)
        user_states.pop(message.from_user.id)
        await message.answer(f"✅ **Channel ID Saved!** Your destination is now `{channel_id}`.", reply_markup=get_settings_keyboard())

    elif state == "awaiting_target_user":
        target = message.text.strip()
        if not target.startswith("@"):
            target = f"@{target}"
        set_setting(message.from_user.id, "default_target", target)
        user_states.pop(message.from_user.id)
        await message.answer(f"✅ **X Target Saved!** X Scraper will default to `{target}`.", reply_markup=get_settings_keyboard())

    elif state == "awaiting_ig_target_user":
        target = message.text.strip().replace("@", "").replace("https://instagram.com/", "").replace("/", "")
        set_setting(message.from_user.id, "ig_default_target", target)
        user_states.pop(message.from_user.id)
        await message.answer(f"✅ **IG Target Saved!** IG Scraper will default to `@{target}`.", reply_markup=get_settings_keyboard())

    elif state == "awaiting_harvest_limit":
        try:
            limit = int(message.text.strip())
            if limit < 1 or limit > 500:
                raise ValueError()
            set_setting(message.from_user.id, "harvest_limit", str(limit))
            user_states.pop(message.from_user.id)
            await message.answer(f"✅ **Harvest Limit Saved!** The scraper will now automatically pull a maximum of `{limit}` items per run.", reply_markup=get_settings_keyboard())
        except ValueError:
            await message.answer("❌ Invalid input. Please enter a valid number between 1 and 500.")

    elif state == "awaiting_new_source":
        url = message.text.strip()
        platform = "unknown"
        if "youtube.com" in url or "youtu.be" in url:
            platform = "youtube"
        elif "twitter.com" in url or "x.com" in url:
            platform = "twitter"
        elif "instagram.com" in url:
            platform = "instagram"
            
        import asyncio
        loop = asyncio.get_event_loop()
        source_id = loop.run_until_complete(add_source_channel(
            user_id=message.from_user.id,
            platform=platform,
            channel_url=url,
            channel_name=url.split('/')[-1],
            collection_name=f"{platform}_auto"
        ))
        user_states.pop(message.from_user.id)
        if source_id:
            await message.answer(f"✅ Added {platform} source! ID: {source_id}")
        else:
            await message.answer("❌ Failed to add source (might already exist).")

    elif state == "awaiting_autocheck_setup":
        data = message.text.strip().split('|')
        import asyncio
        loop = asyncio.get_event_loop()
        
        if len(data) == 2 and data[0].strip().lower() == 'stop':
            source_id = int(data[1].strip())
            loop.run_until_complete(stop_auto_check(source_id))
            await message.answer(f"🛑 Stopped auto-check for source ID {source_id}.")
        elif len(data) == 3:
            try:
                source_id = int(data[0].strip())
                target_id = data[1].strip()
                interval = int(data[2].strip())
                
                # Make sure the target channel is added to db
                tg_id = loop.run_until_complete(add_telegram_channel(message.from_user.id, target_id))
                
                # Create the check
                auto_id = loop.run_until_complete(create_auto_check(
                    user_id=message.from_user.id,
                    source_channel_id=source_id,
                    telegram_channel_id=tg_id,
                    interval_minutes=interval
                ))
                await message.answer(f"✅ Auto-check scheduled every {interval} mins for Source {source_id} -> Target {target_id}")
            except Exception as e:
                await message.answer(f"❌ Error setting up auto-check: {e}")
        else:
            await message.answer("❌ Invalid format. Use: `source_id | target_channel_id | interval_minutes`")
        
        user_states.pop(message.from_user.id)
