from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router, types, F
from app.services.db_manager import (
    get_setting, create_task, get_active_task, 
    set_task_status, get_task_by_id
)

def get_dashboard_keyboard(user_id: int):
    """
    Status-Aware Command Center Keyboard.
    """
    task = get_active_task(user_id)
    buttons = []
    
    if not task:
        buttons.append([InlineKeyboardButton(text="🚀 Start New Harvest", callback_data="setup_harvest")])
    else:
        # State-Based Controls
        status = task.get('status', 'IDLE')
        if status == "PAUSED":
            buttons.append([InlineKeyboardButton(text="▶️ Resume Harvester", callback_data=f"resume_task:{task['task_id']}")])
        else:
            buttons.append([InlineKeyboardButton(text="⏸️ Pause Harvester", callback_data=f"pause_task:{task['task_id']}")])
            
        buttons.append([InlineKeyboardButton(text="🛑 Force Stop", callback_data=f"stop_task:{task['task_id']}")])
        buttons.append([InlineKeyboardButton(text="📊 Refresh Stats", callback_data=f"refresh_stats:{task['task_id']}")])
        
    buttons.append([InlineKeyboardButton(text="⚙️ Settings", callback_data="back_to_settings")])
    buttons.append([InlineKeyboardButton(text="❌ Close Menu", callback_data="close_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_settings_keyboard(user_id: int = 0, context: str = "settings"):
    """
    Main Control Center Keyboard.
    If context is 'harvester_hud', it adds a Stop button.
    """
    buttons = [
        [
            InlineKeyboardButton(text="📡 Set Destination", callback_data="set_channel"),
            InlineKeyboardButton(text="🎯 Set Default Target", callback_data="set_target")
        ],
        [
            InlineKeyboardButton(text="🔢 Set Harvest Limit", callback_data="set_limit"),
            InlineKeyboardButton(text="✅ Verify Channel Access", callback_data="verify_channel")
        ]
    ]
    
    if context == "harvester_hud":
        buttons.insert(0, [InlineKeyboardButton(text="🛑 Stop Harvester", callback_data="stop_harvest")])
    
    buttons.append([InlineKeyboardButton(text="❌ Close Menu", callback_data="close_menu")])
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
