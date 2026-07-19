"""
Main Menu Handler — Start, interceptors, menu routing.
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.bot.keyboards import get_main_reply_keyboard
from app.bot.states import HarvestStates

router = Router(name="menu")

MENU_BUTTONS = [
    "🐦 X Harvest", "📸 IG Harvest", "▶️ YT Harvest",
    "📊 Stats", "📺 Add Source", "⏰ Auto-Check",
    "⚙️ Settings", "🔍 Verify Channel", "📝 Logs"
]

@router.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🚀 **Mister Assistant: Command Center**\n"
        "Control your harvesting operations below. Use the buttons to navigate.",
        reply_markup=get_main_reply_keyboard()
    )

@router.message(F.text.in_(MENU_BUTTONS))
async def menu_interceptor(message: types.Message, state: FSMContext):
    """Intercepts main menu buttons and routes them."""
    await state.clear()
    
    # Import handlers here to avoid circular imports
    from .harvest import btn_x_harvest, btn_ig_harvest, btn_yt_harvest
    from .stats import btn_stats, btn_logs
    from .settings import btn_settings, btn_verify
    from .sources import btn_addsource, btn_autocheck
    
    if message.text == "🐦 X Harvest":
        await btn_x_harvest(message, state)
    elif message.text == "📸 IG Harvest":
        await btn_ig_harvest(message, state)
    elif message.text == "▶️ YT Harvest":
        await btn_yt_harvest(message, state)
    elif message.text == "📊 Stats":
        await btn_stats(message)
    elif message.text == "📺 Add Source":
        await btn_addsource(message, state)
    elif message.text == "⏰ Auto-Check":
        await btn_autocheck(message, state)
    elif message.text == "⚙️ Settings":
        await btn_settings(message)
    elif message.text == "🔍 Verify Channel":
        await btn_verify(message)
    elif message.text == "📝 Logs":
        await btn_logs(message)