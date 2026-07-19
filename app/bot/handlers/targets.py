"""
Targets Handlers — X and IG target processing.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.bot.states import HarvestStates
from .scraper_handlers import execute_scrape_internal
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router(name="targets")

def get_x_mode_keyboard(username: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼️ Media Tab Only", callback_data=f"x_mode|media|{username}")],
        [InlineKeyboardButton(text="🌐 Full Timeline (Quotes + Retweets)", callback_data=f"x_mode|timeline|{username}")],
    ])

@router.message(HarvestStates.awaiting_x_target)
async def process_x_target(message: types.Message, state: FSMContext):
    target = message.text.strip()
    if not target.startswith("@"):
        target = f"@{target}"
    
    await state.clear()
    await message.answer(
        f"🐦 **Target Acquired:** `{target}`\n\n"
        "📡 **Choose scraping mode:**\n"
        "\u2022 **Media Tab** \u2014 Only videos the user uploaded directly\n"
        "\u2022 **Full Timeline** \u2014 Includes embedded quotes & retweets",
        reply_markup=get_x_mode_keyboard(target)
    )


@router.callback_query(F.data.startswith("x_mode|"))
async def cb_x_mode(callback: types.CallbackQuery):
    parts = callback.data.split("|")
    mode = parts[1]     # "media" or "timeline"
    username = parts[2]
    mode_label = "🖼️ Media Tab" if mode == "media" else "🌐 Full Timeline"
    await callback.message.edit_text(f"🚀 Starting **{mode_label}** harvest for `{username}`...")
    await execute_scrape_internal(callback.message, username, "twitter", mode=mode)


@router.message(HarvestStates.awaiting_ig_target)
async def process_ig_target(message: types.Message, state: FSMContext):
    target = message.text.strip().replace("@", "").replace("https://instagram.com/", "").replace("/", "")
    await state.clear()
    await execute_scrape_internal(message, target, "instagram")