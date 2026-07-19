from aiogram import types
from aiogram.fsm.context import FSMContext
from app.data.db_manager import get_setting
from app.data.db_advanced import get_user_telegram_channels
from app.bot.keyboards import get_preflight_destination_keyboard

async def check_destination_preflight(message_or_callback, state: FSMContext, pending_action: str) -> bool:
    """
    Returns True if destination is set and we can proceed.
    Returns False if it intercepted the flow to ask for a destination.
    """
    user_id = message_or_callback.from_user.id
    target_channel = get_setting(user_id, "destination_channel_id")
    
    if target_channel:
        # Check Admin status
        from app.utils.validators import verify_bot_is_admin
        
        bot = message_or_callback.bot
        admin_check = await verify_bot_is_admin(bot, target_channel)
        
        if admin_check['is_valid']:
            return True
        else:
            text = (
                f"🚨 **Security Alert**\n\n"
                f"I cannot post to `{target_channel}`:\n"
                f"_{admin_check['error_message']}_\n\n"
                f"Please fix this in the channel, or set a new destination channel below:"
            )
            
            channels = await get_user_telegram_channels(user_id)
            await state.update_data(pending_action=pending_action)
            keyboard = get_preflight_destination_keyboard(channels)
            
            if isinstance(message_or_callback, types.CallbackQuery):
                await message_or_callback.message.edit_text(text, reply_markup=keyboard)
                await message_or_callback.answer()
            else:
                await message_or_callback.answer(text, reply_markup=keyboard)
                
            return False
            
    # We need to prompt
    channels = await get_user_telegram_channels(user_id)
    
    await state.update_data(pending_action=pending_action)
    
    keyboard = get_preflight_destination_keyboard(channels)
    
    text = (
        "🚨 **Pre-flight Check Required**\n\n"
        "You haven't set a destination channel. Where should I post the scraped media?\n"
        "Select a previously saved channel below or add a new one:"
    )
    
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=keyboard)
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(text, reply_markup=keyboard)
        
    return False

async def resume_pending_action(message_or_callback, state: FSMContext):
    data = await state.get_data()
    pending_action = data.get("pending_action")
    if not pending_action:
        return
        
    await state.update_data(pending_action=None)
    
    # We need to route back to the original function
    # To avoid circular imports, we import them here
    from app.bot.handlers.harvest import btn_x_harvest, btn_ig_harvest, btn_yt_harvest
    
    if pending_action == "x_harvest":
        await btn_x_harvest(message_or_callback, state)
    elif pending_action == "ig_harvest":
        await btn_ig_harvest(message_or_callback, state)
    elif pending_action == "yt_harvest":
        await btn_yt_harvest(message_or_callback, state)
    elif pending_action.startswith("cb_setup|"):
        from app.bot.callbacks import cb_setup
        # Construct a fake callback query if needed, or just let cb_setup handle it
        # cb_setup relies on callback.data to know if it's X or IG
        # Let's pass the original callback data if it was a callback
        original_data = pending_action.split("|")[1]
        if isinstance(message_or_callback, types.CallbackQuery):
            message_or_callback.data = original_data
            await cb_setup(message_or_callback)
        else:
            # If it's a message, we create a dummy callback query
            dummy_cb = types.CallbackQuery(
                id="0",
                from_user=message_or_callback.from_user,
                chat_instance="0",
                message=message_or_callback,
                data=original_data
            )
            await cb_setup(dummy_cb)
    elif pending_action.startswith("run_saved|"):
        from app.bot.handlers.target_handlers import cb_run_saved_target
        original_data = pending_action.split("|")[1]
        if isinstance(message_or_callback, types.CallbackQuery):
            message_or_callback.data = original_data
            await cb_run_saved_target(message_or_callback)
        else:
            dummy_cb = types.CallbackQuery(
                id="0",
                from_user=message_or_callback.from_user,
                chat_instance="0",
                message=message_or_callback,
                data=original_data
            )
            await cb_run_saved_target(dummy_cb)
