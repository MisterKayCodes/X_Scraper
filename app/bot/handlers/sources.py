"""
Sources Handlers — Add source, auto-check.
"""
import asyncio
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from app.bot.states import HarvestStates
from app.data.db_advanced import add_source_channel, stop_auto_check, create_auto_check, add_telegram_channel

router = Router(name="sources")

async def btn_addsource(message: types.Message, state: FSMContext):
    await state.set_state(HarvestStates.awaiting_new_source)
    await message.answer("📺 Send me the URL of the YouTube channel, X profile, or IG profile you want to add.")

async def btn_autocheck(message: types.Message, state: FSMContext):
    await state.set_state(HarvestStates.awaiting_autocheck_setup)
    await message.answer("⚙️ Send me the setup in this format: `source_id | target_channel_id | interval_minutes`\nExample: `1 | -100123456 | 60`\nOr send `stop | source_id` to stop auto-checking for a source.")

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
        
    loop = asyncio.get_event_loop()
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

@router.message(HarvestStates.awaiting_autocheck_setup)
async def process_autocheck(message: types.Message, state: FSMContext):
    data = message.text.strip().split('|')
    loop = asyncio.get_event_loop()
    
    if len(data) == 2 and data[0].strip().lower() == 'stop':
        source_id = int(data[1].strip())
        await stop_auto_check(source_id)
        await message.answer(f"🛑 Stopped auto-check for source ID {source_id}.")
    elif len(data) == 3:
        try:
            source_id = int(data[0].strip())
            target_id = data[1].strip()
            interval = int(data[2].strip())
            
            tg_id = await add_telegram_channel(message.from_user.id, target_id)
            auto_id = await create_auto_check(
                user_id=message.from_user.id,
                source_channel_id=source_id,
                telegram_channel_id=tg_id,
                interval_minutes=interval
            )
            await message.answer(f"✅ Auto-check scheduled every {interval} mins for Source {source_id} -> Target {target_id}")
        except Exception as e:
            await message.answer(f"❌ Error setting up auto-check: {e}")
    else:
        await message.answer("❌ Invalid format. Use: `source_id | target_channel_id | interval_minutes`")
    
    await state.clear()