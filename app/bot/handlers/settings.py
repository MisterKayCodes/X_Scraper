"""
Settings Handlers — Settings, verify, channel ID, limits, duration.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.bot.keyboards import get_settings_keyboard
from app.bot.states import HarvestStates
from app.data.db_manager import get_setting, set_setting

router = Router(name="settings")

async def btn_settings(message: types.Message):
    await message.answer("🛠️ **Mister Assistant Settings**\nManage your destination and targets below:", reply_markup=get_settings_keyboard())

async def btn_verify(message: types.Message):
    channel_id = get_setting(message.from_user.id, "destination_channel_id")
    if not channel_id:
        await message.answer("❌ No channel set! Set it in Settings first.")
        return
    try:
        await message.bot.send_message(channel_id, "✅ **Channel Handshake Successful!**\nThis channel is now linked.")
        await message.answer(f"✅ Verified! Sent test message to {channel_id}")
    except Exception as e:
        await message.answer(f"❌ Verification Failed: {e}")

@router.message(HarvestStates.awaiting_channel_id)
async def process_channel_id(message: types.Message, state: FSMContext):
    channel_id = None
    
    if message.forward_from_chat:
        channel_id = str(message.forward_from_chat.id)
    elif message.text:
        text = message.text.strip()
        if text.startswith("-100"):
            channel_id = text
        elif text.startswith("@") or "t.me/" in text:
            username = text.split("/")[-1].replace("@", "")
            try:
                chat = await message.bot.get_chat(f"@{username}")
                channel_id = str(chat.id)
            except Exception as e:
                await message.answer(f"❌ **Resolution Failed:** Could not find a channel named `{username}`.")
                return

    if not channel_id:
        await message.answer("❌ Invalid input. Please **forward a message** from your channel or send a `@username`.")
        return

    set_setting(message.from_user.id, "destination_channel_id", channel_id)
    
    # Check if there is a pending action to resume
    data = await state.get_data()
    pending_action = data.get("pending_action")
    
    await state.clear()
    
    if pending_action:
        await message.answer(f"✅ **Channel ID Saved!** Resuming your previous action...")
        from app.bot.preflight import resume_pending_action
        # We need to re-inject pending_action because we cleared state
        await state.update_data(pending_action=pending_action)
        await resume_pending_action(message, state)
    else:
        await message.answer(f"✅ **Channel ID Saved!** Your destination is now `{channel_id}`.", reply_markup=get_settings_keyboard())

@router.message(HarvestStates.awaiting_harvest_limit)
async def process_harvest_limit(message: types.Message, state: FSMContext):
    try:
        limit = int(message.text.strip())
        if limit < 1 or limit > 500:
            raise ValueError()
        set_setting(message.from_user.id, "harvest_limit", str(limit))
        await state.clear()
        await message.answer(f"✅ **Harvest Limit Saved!** Default: `{limit}` items.", reply_markup=get_settings_keyboard())
    except ValueError:
        await message.answer("❌ Invalid number.")

@router.message(HarvestStates.awaiting_max_duration)
async def process_max_duration(message: types.Message, state: FSMContext):
    try:
        mins = int(message.text.strip())
        if mins < 1:
            raise ValueError()
        set_setting(message.from_user.id, "max_duration_seconds", str(mins * 60))
        await state.clear()
        await message.answer(f"✅ **Max Duration Saved!** Skipping videos longer than `{mins}` minutes.", reply_markup=get_settings_keyboard())
    except ValueError:
        await message.answer("❌ Invalid number.")