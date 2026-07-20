from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.bot.states import HarvestStates
from app.data.db_manager import (
    get_setting, create_task, get_active_task, 
    set_task_status, get_task_by_id
)
from app.bot.keyboards import get_settings_keyboard, get_verify_keyboard, get_dashboard_keyboard
from app.services.profile_scraper import scrape_profile_media
from app.services.ig_scraper import scrape_ig_profile_media
from app.bot.queue_worker import harvester_queue

from app.bot.preflight import resume_pending_action

router = Router()

@router.callback_query(F.data == "set_destination")
async def cb_set_channel(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(HarvestStates.awaiting_channel_id)
    text = (
        "🔗 **Set Destination Channel**\n\n"
        "You can link your channel in **one of three ways**:\n"
        "1. **Forward a message** from the channel to me.\n"
        "2. Send the **@username** of the channel (if public).\n"
        "3. Paste the raw **ID** (starts with `-100`)."
    )
    await callback.message.edit_text(text, reply_markup=get_verify_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("pf_set_dest|"))
async def cb_pf_set_dest(callback: types.CallbackQuery, state: FSMContext):
    channel_id = callback.data.replace("pf_set_dest|", "")
    from app.data.db_manager import set_setting
    set_setting(callback.from_user.id, "destination_channel_id", channel_id)
    await callback.answer("✅ Channel selected!", show_alert=False)
    # Resume the pending action
    await resume_pending_action(callback, state)

@router.callback_query(F.data == "pf_set_new_dest")
async def cb_pf_set_new_dest(callback: types.CallbackQuery, state: FSMContext):
    # This just redirects to the normal set_destination flow, but keeps pending_action intact
    await cb_set_channel(callback, state)



@router.callback_query(F.data == "set_limit")
async def cb_set_limit(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(HarvestStates.awaiting_harvest_limit)
    await callback.message.edit_text("🔢 **Enter the new maximum number of items to harvest per run (e.g., 20):**")
    await callback.answer()

@router.callback_query(F.data == "set_duration")
async def cb_set_duration(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(HarvestStates.awaiting_max_duration)
    await callback.message.edit_text("⏱️ **Enter the max duration for videos in minutes (e.g., 10):**\nVideos longer than this will be skipped.")
    await callback.answer()

@router.callback_query(F.data == "verify_channel")
async def cb_verify(callback: types.CallbackQuery):
    channel_id = get_setting(callback.from_user.id, "destination_channel_id")
    if not channel_id:
        await callback.answer("❌ No channel set! Use 'Set Destination' first.", show_alert=True)
        return
    
    try:
        test_msg = await callback.bot.send_message(channel_id, "✅ **Channel Handshake Successful!**\nThis channel is now linked to your Harvester.")
        await callback.answer(f"✅ Verified! Sent test message to {channel_id}", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Verification Failed: {e}", show_alert=True)

@router.callback_query(F.data.in_(["settings_menu", "back_to_settings"]))
async def cb_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛠️ **Mister Assistant Settings**\nManage your destination and targets below:", reply_markup=get_settings_keyboard())
    await callback.answer()

@router.callback_query(F.data.in_(["setup_harvest_x", "setup_harvest_ig"]))
async def cb_setup(callback: types.CallbackQuery, state: FSMContext = None):
    # If state is None (e.g. dummy callback from preflight), we might not be able to do FSMContext operations.
    # But aiogram injects state automatically if requested.
    is_ig = (callback.data == "setup_harvest_ig")
    platform_name = "Instagram" if is_ig else "X (Twitter)"
    
    # Use the correct target key for each platform
    target_key = "ig_default_target" if is_ig else "default_target"
    target = get_setting(callback.from_user.id, target_key)
    
    if not target:
        platform_label = "IG" if is_ig else "X"
        await callback.answer(f"🚨 No {platform_label} target set! Go to Settings → Set {platform_label} Target first.", show_alert=True)
        return
        
    from app.bot.preflight import check_destination_preflight
    # Check preflight. If it intercepts, it will return False.
    if state and not await check_destination_preflight(callback, state, f"cb_setup|{callback.data}"):
        return
    # If state is None, it means we are already resuming from preflight, so we know destination is set.
    
    channel = get_setting(callback.from_user.id, "destination_channel_id")
    if not channel:
        await callback.answer("🚨 No destination channel set! Go to Settings → Set Destination first.", show_alert=True)
        return
        
    await callback.answer(f"🚀 Radar Engaged for {platform_name}! Searching for media...", show_alert=True)
    task_id = create_task(callback.from_user.id, target)
    
    async def update_status(text: str):
        try:
            await callback.message.edit_text(text)
        except Exception:
            pass
            
    # Fetch user defined limit
    limit_str = get_setting(callback.from_user.id, "harvest_limit")
    scrape_limit = int(limit_str) if limit_str else 20
            
    # 1. Scrape
    if is_ig:
        links = await scrape_ig_profile_media(target, callback.from_user.id, limit=scrape_limit, status_callback=update_status)
    else:
        links = await scrape_profile_media(target, callback.from_user.id, limit=scrape_limit, status_callback=update_status)
    
    if not links:
        set_task_status(task_id, 'STOPPED')
        await callback.message.edit_text(f"❌ **Radar Failure:** No new media for {target}.")
        return
        
    # 2. Update Task & Queue
    await callback.message.edit_text(f"📡 **Harvester Loaded:** {len(links)} items found. Starting Conveyor...")
    from app.data.db_manager import update_task_meta
    update_task_meta(task_id, len(links), callback.message.message_id)
    
    for link in links:
        await harvester_queue.put((link, callback.from_user.id, task_id))
    
@router.callback_query(F.data.startswith("pause_task:"))
async def cb_pause(callback: types.CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    set_task_status(task_id, "PAUSED")
    await callback.answer("⏸️ Harvester Paused.", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=get_dashboard_keyboard(callback.from_user.id))

@router.callback_query(F.data.startswith("resume_task:"))
async def cb_resume(callback: types.CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    set_task_status(task_id, "QUEUED")
    await callback.answer("▶️ Harvester Resumed.", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=get_dashboard_keyboard(callback.from_user.id))

@router.callback_query(F.data.startswith("skip_task:"))
async def cb_skip(callback: types.CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    set_task_status(task_id, "SKIP_CURRENT")
    await callback.answer("⏭️ Skipping item and resuming...", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=get_dashboard_keyboard(callback.from_user.id))

@router.callback_query(F.data.startswith("stop_task:"))
async def cb_stop(callback: types.CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    set_task_status(task_id, "STOPPED")
    await callback.answer("🛑 Harvester Force Stopped.", show_alert=True)
    await callback.message.edit_reply_markup(reply_markup=get_dashboard_keyboard(callback.from_user.id))

@router.callback_query(F.data.startswith("refresh_stats:"))
async def cb_refresh(callback: types.CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    task = get_task_by_id(task_id)
    if not task:
        await callback.answer("⚠️ Task not found.")
        return
        
    efficiency = (task['success_count'] / max(1, task['processed_count'])) * 100
    storage_mb = task['storage_kb'] / 1024
    
    # Simple ETA logic: 20s per remaining item
    remaining = task['total_items'] - task['processed_count']
    eta_m = (remaining * 20) // 60
    
    stats_text = (
        f"📊 **Enterprise Stats Card**\n"
        f"───────────────────\n"
        f"🎯 **Target:** @{task['target_username'].replace('@', '')}\n"
        f"⏳ **Status:** {task['status']}\n"
        f"📥 **File:** `Fetching updates...`\n\n"
        f"📈 **Efficiency:** {efficiency:.1f}%\n"
        f"📦 **Posted:** {task['success_count']} / {task['total_items']}\n"
        f"💾 **Storage Saved:** {storage_mb:.2f} MB\n"
        f"⏱️ **ETA:** ~{int(eta_m)} mins remaining\n"
        f"───────────────────"
    )
    
    try:
        await callback.message.edit_text(stats_text, reply_markup=get_dashboard_keyboard(callback.from_user.id))
    except Exception:
        pass # Message is same
    await callback.answer()

@router.callback_query(F.data == "close_menu")
async def cb_close(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.answer()
