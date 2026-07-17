import asyncio
import logging
import sys
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from app.config import TELEGRAM_BOT_TOKEN, API_PORT
from app.bot.handlers import router as command_router
from app.bot.callbacks import router as callback_router
from app.data.db_manager import init_db
from app.bot.queue_worker import queue_consumer
from app.services.scheduler import run_auto_check_loop
from app.api import app as fastapi_app

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("mister_launcher")

async def run_bot(bot: Bot, dp: Dispatcher):
    """Starts the Telegram Bot Polling"""
    logger.info("[BOT] Starting Aiogram polling...")
    await dp.start_polling(bot)

async def run_api():
    """Starts the FastAPI Service"""
    logger.info(f"[API] Starting FastAPI on port {API_PORT}...")
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=API_PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    if TELEGRAM_BOT_TOKEN == "REPLACE_ME":
        logger.error("[!] ERROR: Please set your TELEGRAM_BOT_TOKEN in config.py or via environment variables.")
        return

    # Initialize Bot and Dispatcher
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Initialize Database
    init_db()

    # Register Routers
    dp.include_router(command_router)
    dp.include_router(callback_router)

    # Start ALL layers simultaneously
    logger.info("🚀 Mister Assistant is launching all systems...")
    
    await asyncio.gather(
        queue_consumer(bot), # Background Harvester Worker
        run_auto_check_loop(), # Background Scheduler for Auto-Checking
        run_api(),           # FastAPI Service Layer
        run_bot(bot, dp)     # Telegram Bot Interface
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("[OK] System Shutdown.")
