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

def get_x_limit_keyboard(mode: str, username: str):
    """Quick-pick limit buttons, mirrors YouTube's UX."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="10",  callback_data=f"x_limit|10|{mode}|{username}"),
            InlineKeyboardButton(text="20",  callback_data=f"x_limit|20|{mode}|{username}"),
            InlineKeyboardButton(text="50",  callback_data=f"x_limit|50|{mode}|{username}"),
        ],
        [InlineKeyboardButton(text="📦 Max (100)", callback_data=f"x_limit|100|{mode}|{username}")],
        [InlineKeyboardButton(text="✏️ Custom number...", callback_data=f"x_limit|custom|{mode}|{username}")],
    ])


# ─── Step 1: User types username ───────────────────────────────────────────
@router.message(HarvestStates.awaiting_x_target)
async def process_x_target(message: types.Message, state: FSMContext):
    target = message.text.strip()
    if not target.startswith("@"):
        target = f"@{target}"
    
    await state.clear()
    await message.answer(
        f"🐦 **Target Acquired:** `{target}`\n\n"
        "📡 **Choose scraping mode:**\n"
        "• **Media Tab** — Only videos the user uploaded directly\n"
        "• **Full Timeline** — Includes embedded quotes & retweets",
        reply_markup=get_x_mode_keyboard(target)
    )


# ─── Step 2: User picks mode → show limit picker ───────────────────────────
@router.callback_query(F.data.startswith("x_mode|"))
async def cb_x_mode(callback: types.CallbackQuery):
    parts = callback.data.split("|")
    mode = parts[1]       # "media" or "timeline"
    username = parts[2]
    mode_label = "🖼️ Media Tab" if mode == "media" else "🌐 Full Timeline"
    await callback.message.edit_text(
        f"🐦 **Mode:** {mode_label} → `{username}`\n\n"
        "🔢 **How many posts do you want to harvest?**",
        reply_markup=get_x_limit_keyboard(mode, username)
    )


# ─── Step 3a: User picks a preset limit ────────────────────────────────────
@router.callback_query(F.data.startswith("x_limit|"))
async def cb_x_limit(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("|")
    limit_choice = parts[1]   # "10", "20", "50", "100", or "custom"
    mode = parts[2]
    username = parts[3]

    if limit_choice == "custom":
        # Save context and ask for number
        await state.set_state(HarvestStates.awaiting_x_limit)
        await state.update_data(x_mode=mode, x_username=username)
        await callback.message.edit_text(
            f"✏️ **Custom Limit for** `{username}`\n\n"
            "Send me a number (e.g. `35`):"
        )
        return

    limit = int(limit_choice)
    mode_label = "🖼️ Media Tab" if mode == "media" else "🌐 Full Timeline"
    await callback.message.edit_text(
        f"🚀 Starting **{mode_label}** harvest for `{username}` — limit: **{limit}**..."
    )
    await execute_scrape_internal(
        callback.message, callback.from_user.id,
        username, "twitter", override_limit=limit, mode=mode
    )


# ─── Step 3b: User types a custom limit number ─────────────────────────────
@router.message(HarvestStates.awaiting_x_limit)
async def process_x_custom_limit(message: types.Message, state: FSMContext):
    data = await state.get_data()
    mode = data.get("x_mode", "media")
    username = data.get("x_username", "")
    await state.clear()

    if not message.text.strip().isdigit():
        await message.answer("⚠️ Please send a valid number (e.g. `35`).")
        return

    limit = int(message.text.strip())
    mode_label = "🖼️ Media Tab" if mode == "media" else "🌐 Full Timeline"
    await message.answer(
        f"🚀 Starting **{mode_label}** harvest for `{username}` — limit: **{limit}**..."
    )
    await execute_scrape_internal(
        message, message.from_user.id,
        username, "twitter", override_limit=limit, mode=mode
    )


# ─── IG target (no mode picker needed) ─────────────────────────────────────
@router.message(HarvestStates.awaiting_ig_target)
async def process_ig_target(message: types.Message, state: FSMContext):
    target = message.text.strip().replace("@", "").replace("https://instagram.com/", "").replace("/", "")
    await state.clear()
    await execute_scrape_internal(message, message.from_user.id, target, "instagram")