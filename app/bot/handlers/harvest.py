"""
Harvest Handlers — X, IG, YouTube harvest buttons.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.bot.states import HarvestStates
from app.bot.keyboards import get_harvest_target_selection
from app.data.db_manager import get_saved_targets

router = Router(name="harvest")

async def btn_x_harvest(message: types.Message, state: FSMContext):
    from app.bot.preflight import check_destination_preflight
    if not await check_destination_preflight(message, state, "x_harvest"): return
    
    targets = get_saved_targets(message.from_user.id, "twitter")
    if targets:
        await message.answer("🐦 **X Harvest:** Select a saved target or type a new one:", reply_markup=get_harvest_target_selection("twitter", targets))
    else:
        await state.set_state(HarvestStates.awaiting_x_target)
        await message.answer("🐦 **Type the X (Twitter) Username to track:** (e.g. `@MisterKayCodes`)")

async def btn_ig_harvest(message: types.Message, state: FSMContext):
    from app.bot.preflight import check_destination_preflight
    if not await check_destination_preflight(message, state, "ig_harvest"): return
    
    targets = get_saved_targets(message.from_user.id, "instagram")
    if targets:
        await message.answer("📸 **IG Harvest:** Select a saved target or type a new one:", reply_markup=get_harvest_target_selection("instagram", targets))
    else:
        await state.set_state(HarvestStates.awaiting_ig_target)
        await message.answer("📸 **Type the Instagram Username to track:** (e.g. `@nasa`)")

async def btn_yt_harvest(message: types.Message, state: FSMContext):
    from app.bot.preflight import check_destination_preflight
    if not await check_destination_preflight(message, state, "yt_harvest"): return
    
    targets = get_saved_targets(message.from_user.id, "youtube")
    if targets:
        await message.answer("▶️ **YouTube Harvest:** Select a saved target or type a new one:", reply_markup=get_harvest_target_selection("youtube", targets))
    else:
        await state.set_state(HarvestStates.awaiting_yt_url)
        await message.answer("▶️ **YouTube Harvest:**\n\nSend me a YouTube **channel URL** or **video link** to process.")