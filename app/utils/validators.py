import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

logger = logging.getLogger("validators")

async def verify_bot_is_admin(bot: Bot, channel_id: str | int) -> dict:
    """
    Verifies if the bot is an administrator in the specified channel and has permission to post messages.
    Returns:
        dict: {
            'is_valid': bool,
            'is_admin': bool,
            'can_post': bool,
            'error_message': str | None
        }
    """
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        
        if member.status == "administrator":
            # Check specific permissions
            can_post = getattr(member, 'can_post_messages', False)
            if can_post:
                return {'is_valid': True, 'is_admin': True, 'can_post': True, 'error_message': None}
            else:
                return {
                    'is_valid': False, 
                    'is_admin': True, 
                    'can_post': False, 
                    'error_message': "Bot is an Admin, but lacks the 'Post Messages' permission."
                }
        
        elif member.status == "creator":
            return {'is_valid': True, 'is_admin': True, 'can_post': True, 'error_message': None}
            
        else:
            return {
                'is_valid': False, 
                'is_admin': False, 
                'can_post': False, 
                'error_message': "Bot is NOT an Admin in this channel. Please promote it to Admin."
            }
            
    except TelegramBadRequest:
        return {'is_valid': False, 'is_admin': False, 'can_post': False, 'error_message': "Invalid channel ID or channel not found."}
    except TelegramForbiddenError:
        return {'is_valid': False, 'is_admin': False, 'can_post': False, 'error_message': "Bot was kicked or has no access to this channel."}
    except Exception as e:
        logger.error(f"[VALIDATOR] Error verifying admin status for {channel_id}: {e}")
        return {'is_valid': False, 'is_admin': False, 'can_post': False, 'error_message': f"Unexpected error: {str(e)}"}
