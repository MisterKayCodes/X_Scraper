from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    # Placeholder for future interactions
    # builder.add(types.InlineKeyboardButton(text="Help", callback_data="help"))
    return builder.as_markup()
