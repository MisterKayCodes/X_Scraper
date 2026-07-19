from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.bot.states import TargetCRUDStates, HarvestStates
from app.data.db_manager import add_saved_target, delete_saved_target, get_saved_targets
from app.bot.keyboards import get_targets_keyboard, get_settings_keyboard
from .scraper_handlers import execute_scrape_internal

router = Router()

@router.callback_query(F.data == "manage_targets")
async def cb_manage_targets(callback: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🐦 Manage X Targets", callback_data="view_targets_twitter")],
        [types.InlineKeyboardButton(text="📸 Manage IG Targets", callback_data="view_targets_instagram")],
        [types.InlineKeyboardButton(text="▶️ Manage YT Targets", callback_data="view_targets_youtube")],
        [types.InlineKeyboardButton(text="🔙 Back to Settings", callback_data="settings_menu")]
    ])
    await callback.message.edit_text("🎯 **Manage Saved Targets**\nSelect a platform to manage:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("view_targets_"))
async def cb_view_targets(callback: types.CallbackQuery):
    platform = callback.data.replace("view_targets_", "")
    targets = get_saved_targets(callback.from_user.id, platform)
    
    emoji = "▶️ YT" if platform == "youtube" else ("🐦 X" if platform == "twitter" else "📸 IG")
    await callback.message.edit_text(
        f"🎯 **Saved {emoji} Targets**\nYou have {len(targets)} saved target(s).",
        reply_markup=get_targets_keyboard(platform, targets)
    )

@router.callback_query(F.data.startswith("del_target_"))
async def cb_delete_target(callback: types.CallbackQuery):
    target_id = int(callback.data.replace("del_target_", ""))
    delete_saved_target(target_id, callback.from_user.id)
    await callback.answer("✅ Target deleted!", show_alert=True)
    # Refresh view
    # Note: we need platform to refresh properly. It's not in the callback_data but we can just go back to settings or ignore for simplicity here.
    await callback.message.edit_text("✅ Target deleted. Returning to Settings...", reply_markup=get_settings_keyboard())

@router.callback_query(F.data.startswith("add_target_"))
async def cb_add_target(callback: types.CallbackQuery, state: FSMContext):
    platform = callback.data.replace("add_target_", "")
    
    if platform == "twitter":
        await state.set_state(TargetCRUDStates.awaiting_new_x_target)
        await callback.message.edit_text("🐦 **Send the X (Twitter) Username to save:** (e.g. `@MisterKayCodes`)")
    elif platform == "instagram":
        await state.set_state(TargetCRUDStates.awaiting_new_ig_target)
        await callback.message.edit_text("📸 **Send the IG Username to save:**")
    elif platform == "youtube":
        await state.set_state(TargetCRUDStates.awaiting_new_yt_target)
        await callback.message.edit_text("▶️ **Send the YouTube Channel URL or Handle to save:**")

@router.message(TargetCRUDStates.awaiting_new_x_target)
async def process_new_x_target(message: types.Message, state: FSMContext):
    target = message.text.strip()
    if not target.startswith("@"): target = f"@{target}"
    
    if add_saved_target(message.from_user.id, "twitter", target):
        await message.answer(f"✅ Target `{target}` saved!", reply_markup=get_settings_keyboard())
    else:
        await message.answer(f"❌ Target `{target}` already exists.", reply_markup=get_settings_keyboard())
    await state.clear()

@router.message(TargetCRUDStates.awaiting_new_ig_target)
async def process_new_ig_target(message: types.Message, state: FSMContext):
    target = message.text.strip().replace("@", "").replace("https://instagram.com/", "").replace("/", "")
    
    if add_saved_target(message.from_user.id, "instagram", target):
        await message.answer(f"✅ Target `@{target}` saved!", reply_markup=get_settings_keyboard())
    else:
        await message.answer(f"❌ Target `@{target}` already exists.", reply_markup=get_settings_keyboard())
    await state.clear()

@router.message(TargetCRUDStates.awaiting_new_yt_target)
async def process_new_yt_target(message: types.Message, state: FSMContext):
    target = message.text.strip()
    if target.startswith("@"):
        target = f"https://youtube.com/{target}"
    
    if add_saved_target(message.from_user.id, "youtube", target):
        await message.answer(f"✅ Target `{target}` saved!", reply_markup=get_settings_keyboard())
    else:
        await message.answer(f"❌ Target `{target}` already exists.", reply_markup=get_settings_keyboard())
    await state.clear()

@router.callback_query(F.data.startswith("type_new_target_"))
async def cb_type_new_target_for_harvest(callback: types.CallbackQuery, state: FSMContext):
    platform = callback.data.replace("type_new_target_", "")
    if platform == "twitter":
        await state.set_state(HarvestStates.awaiting_x_target)
        await callback.message.edit_text("🐦 **Type the X (Twitter) Username to track:**")
    elif platform == "instagram":
        await state.set_state(HarvestStates.awaiting_ig_target)
        await callback.message.edit_text("📸 **Type the IG Username to track:**")
    elif platform == "youtube":
        await state.set_state(HarvestStates.awaiting_yt_url)
        await callback.message.edit_text("▶️ **Type the YouTube Channel URL or Handle to track:**")

@router.callback_query(F.data.startswith("run_harvest_"))
async def cb_run_saved_target(callback: types.CallbackQuery, state: FSMContext = None):
    parts = callback.data.split("_")
    platform = parts[2]
    target_id = int(parts[3])
    
    from app.bot.preflight import check_destination_preflight
    if state and not await check_destination_preflight(callback, state, f"run_saved|{callback.data}"):
        return
        
    targets = get_saved_targets(callback.from_user.id, platform)
    target_username = next((t['target_username'] for t in targets if t['id'] == target_id), None)
    
    if not target_username:
        await callback.answer("❌ Target not found.", show_alert=True)
        return
        
    if platform == "youtube":
        from .yt_handlers import get_yt_filter_keyboard
        await callback.message.edit_text(
            f"🎯 Target Acquired: {target_username}\n\n"
            "What type of content do you want to harvest from this channel?",
            reply_markup=get_yt_filter_keyboard(target_username)
        )
    elif platform == "twitter":
        from .targets import get_x_mode_keyboard
        await callback.message.edit_text(
            f"🐦 **Target Acquired:** `{target_username}`\n\n"
            "📡 **Choose scraping mode:**\n"
            "• **Media Tab** — Only videos the user uploaded directly\n"
            "• **Full Timeline** — Includes embedded quotes & retweets",
            reply_markup=get_x_mode_keyboard(target_username)
        )
    else:
        await callback.message.edit_text(f"🚀 Starting harvest for {target_username}...")
        await execute_scrape_internal(callback.message, target_username, platform)

