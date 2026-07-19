import sys
from loguru import logger
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from typing import Callable, Dict, Any, Awaitable
import traceback
import pathlib

# Ensure logs directory exists
log_dir = pathlib.Path("app/logs")
log_dir.mkdir(parents=True, exist_ok=True)

# Configure Loguru
logger.remove() # Remove default handler
# Add console handler
logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>", level="INFO")
# Add file handler with rotation
logger.add(log_dir / "bot.log", rotation="10 MB", retention="5 days", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name} - {message}", level="DEBUG")

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        
        user_id = None
        username = "Unknown"
        action = "Unknown Action"
        
        # Determine the event type and extract details
        if getattr(event, 'message', None):
            user_id = event.message.from_user.id
            username = event.message.from_user.username or event.message.from_user.first_name
            action = f"Message: '{event.message.text}'" if event.message.text else "Non-text message"
        elif getattr(event, 'callback_query', None):
            user_id = event.callback_query.from_user.id
            username = event.callback_query.from_user.username or event.callback_query.from_user.first_name
            action = f"Callback: '{event.callback_query.data}'"
            
        if user_id:
            logger.info(f"[User {user_id} | @{username}] {action}")
            
        try:
            # Continue the handler chain
            result = await handler(event, data)
            return result
        except Exception as e:
            # Catch all unhandled exceptions
            logger.error(f"Unhandled Exception for User {user_id}: {e}\n{traceback.format_exc()}")
            # We don't suppress it, let Aiogram handle it too if needed, or suppress it and notify user
            if getattr(event, 'message', None):
                try:
                    await event.message.answer("❌ **An unexpected internal error occurred.**\nPlease check the logs.")
                except:
                    pass
            elif getattr(event, 'callback_query', None):
                try:
                    await event.callback_query.message.answer("❌ **An unexpected internal error occurred.**\nPlease check the logs.")
                except:
                    pass
            # Don't re-raise, we handled it gracefully
            return None
