from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram import Router, types, F
from app.data.db_manager import (
    get_setting, create_task, get_active_task, 
    set_task_status, get_task_by_id
)

def get_main_reply_keyboard():
    """
    Persistent Main Menu Keyboard (Reply Keyboard)
    """
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🐦 X Harvest"), KeyboardButton(text="📸 IG Harvest"), KeyboardButton(text="▶️ YT Harvest")],
            [KeyboardButton(text="📊 Stats"), KeyboardButton(text="📺 Add Source"), KeyboardButton(text="🤖 Auto-Harvest")],
            [KeyboardButton(text="⚙️ Settings"), KeyboardButton(text="🔍 Verify Channel")],
            [KeyboardButton(text="📋 Active Tasks"), KeyboardButton(text="📝 Logs")]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

def get_dashboard_keyboard(user_id: int):
    """
    Status-Aware Command Center Keyboard.
    """
    task = get_active_task(user_id)
    buttons = []
    
    if not task:
        buttons.append([InlineKeyboardButton(text="🚀 Start X Harvest", callback_data="setup_harvest_x")])
        buttons.append([InlineKeyboardButton(text="📸 Start IG Harvest", callback_data="setup_harvest_ig")])
    else:
        # State-Based Controls
        status = task.get('status', 'IDLE')
        if status == "PAUSED":
            buttons.append([
                InlineKeyboardButton(text="▶️ Retry & Resume", callback_data=f"resume_task:{task['task_id']}"),
                InlineKeyboardButton(text="⏭️ Skip & Resume", callback_data=f"skip_task:{task['task_id']}")
            ])
        else:
            buttons.append([InlineKeyboardButton(text="⏸️ Pause Harvester", callback_data=f"pause_task:{task['task_id']}")])
            
        buttons.append([InlineKeyboardButton(text="🛑 Force Stop", callback_data=f"stop_task:{task['task_id']}")])
        buttons.append([InlineKeyboardButton(text="🔄 Enable Auto-Check", callback_data=f"setup_autocheck:{task['task_id']}")])
        buttons.append([InlineKeyboardButton(text="📊 Refresh Stats", callback_data=f"refresh_stats:{task['task_id']}")])
        
    buttons.append([InlineKeyboardButton(text="⚙️ Settings", callback_data="back_to_settings")])
    buttons.append([InlineKeyboardButton(text="❌ Close Menu", callback_data="close_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_settings_keyboard():
    """
    Control Panel for global settings.
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎯 Manage Targets", callback_data="manage_targets")
        ],
        [
            InlineKeyboardButton(text="📡 Set Destination Channel", callback_data="set_destination")
        ],
        [
            InlineKeyboardButton(text="🔢 Set Harvest Limit", callback_data="set_limit"),
            InlineKeyboardButton(text="⏱️ Set Max Duration", callback_data="set_duration")
        ]
    ])
    return keyboard

def get_targets_keyboard(platform: str, targets: list):
    """
    Shows a list of saved targets for a specific platform.
    """
    buttons = []
    for t in targets:
        buttons.append([InlineKeyboardButton(text=f"❌ Delete {t['target_username']}", callback_data=f"del_target_{t['id']}")])
    
    # Add new button at the bottom
    buttons.append([InlineKeyboardButton(text="➕ Add New Target", callback_data=f"add_target_{platform}")])
    buttons.append([InlineKeyboardButton(text="🔙 Back to Settings", callback_data="back_to_settings")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_harvest_target_selection(platform: str, targets: list):
    """
    Shows a list of saved targets to click and start harvesting immediately.
    """
    buttons = []
    for t in targets:
        buttons.append([InlineKeyboardButton(text=t['target_username'], callback_data=f"run_harvest_{platform}_{t['id']}")])
        
    buttons.append([InlineKeyboardButton(text="➕ Type a new one...", callback_data=f"type_new_target_{platform}")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_verify_keyboard():
    """
    Keyboard for during channel verification
    """
    buttons = [
        [InlineKeyboardButton(text="🔙 Back to Settings", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_start_keyboard():
    """
    Minimal Start Keyboard
    """
    buttons = [
        [InlineKeyboardButton(text="🛠️ Open Settings Menu", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_preflight_destination_keyboard(channels: list):
    """
    Keyboard for selecting a destination channel during pre-flight check.
    """
    buttons = []
    for ch in channels:
        label = ch.get('channel_title') or ch.get('channel_id')
        buttons.append([InlineKeyboardButton(text=f"📡 {label}", callback_data=f"pf_set_dest|{ch['channel_id']}")])
        
    buttons.append([InlineKeyboardButton(text="➕ Add New Channel", callback_data="pf_set_new_dest")])
    buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="close_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)