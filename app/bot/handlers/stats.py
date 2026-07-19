"""
Stats Handlers — Stats and Logs.
"""
from aiogram import Router, types
from pathlib import Path
from app.data.db_manager import get_user_aggregated_stats

router = Router(name="stats")

async def btn_stats(message: types.Message):
    stats = get_user_aggregated_stats(message.from_user.id)
    
    if stats['total_tasks'] == 0:
        await message.answer("📊 **Global Content Stats**\n\nYou haven't started any harvesting tasks yet!")
        return
        
    storage_mb = (stats['all_time_storage_kb'] or 0) / 1024
    success = stats['all_time_success'] or 0
    total = stats['all_time_items'] or 0
    efficiency = (success / max(1, total)) * 100
    
    stats_text = (
        f"📊 **Global Content Stats**\n"
        f"───────────────────\n"
        f"🚀 **Total Tasks Run:** {stats['total_tasks']}\n"
        f"📦 **Total Items Found:** {total}\n"
        f"✅ **Total Successfully Posted:** {success}\n"
        f"📈 **Lifetime Efficiency:** {efficiency:.1f}%\n"
        f"💾 **Total Storage Saved:** {storage_mb:.2f} MB\n"
        f"───────────────────"
    )
    
    await message.answer(stats_text)

async def btn_logs(message: types.Message):
    try:
        log_path = Path("app/logs/bot.log")
        if not log_path.exists():
            await message.answer("No logs found.")
            return
            
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        last_lines = lines[-30:]
        log_text = "".join(last_lines)
        
        if len(log_text) > 4000:
            log_text = log_text[-4000:]
            
        await message.answer(f"📝 **Recent System Logs:**\n```\n{log_text}\n```", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Error reading logs: {e}")