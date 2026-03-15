import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from app.config import TELEGRAM_BOT_TOKEN
from app.bot.handlers import router

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    if TELEGRAM_BOT_TOKEN == "REPLACE_ME":
        print("[!] ERROR: Please set your TELEGRAM_BOT_TOKEN in config.py or via environment variables.")
        return

    # Initialize Bot and Dispatcher
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN, 
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Register Routers
    dp.include_router(router)

    print("[...] Mister Assistant is starting...")
    
    # Start Polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[OK] Stopped.")
