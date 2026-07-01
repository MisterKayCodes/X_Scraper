import asyncio
import os
from telethon import TelegramClient, errors
from telethon.sessions import StringSession

async def test_session(session_string, api_id, api_hash):
    print(f"Testing session with API_ID={api_id}...")
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("FAILED: Session is NOT authorized (Logged out).")
            return False
            
        me = await client.get_me()
        print(f"SUCCESS! Connected as: {me.first_name} (@{me.username or 'N/A'})")
        return True
    except errors.UserDeactivatedError:
        print("FAILED: User is deactivated (Deleted).")
    except Exception as e:
        print(f"FAILED: Unknown error: {e}")
    finally:
        await client.disconnect()
    return False

if __name__ == '__main__':
    # Use the target session string
    session_str = "1AZWarzIBu7CMPiwprHvbgeM+WiX7VKGkxWOyQgYhdbRt5aAsUeKq5kNVn34XDfh6WCMyvLpEkyG21PwhDbJCIIOYvHCc/r+yqZFF7sMTLkXKYCoQDY2ggqz6KLEYvxvvfRJwki7jEXbBOLt6+9heUurvi66lYDq2z/L+lm8heVhfhmRR1+jSuUj1ds+cgr6FVcCY0Pz7kxYpiKpxq2vo9vabjQbXrklqm4usBO8yHSM6Nc/5Lq6RloZAqUausul+SUmzTzhwm/Rnm4J1XsXRIpDf9KLoSFjRW4Kyn3cYt2phZV3x0DvROCdDoyxBPB5tWj4AcGxhX4HEralFjr33akxKmhqJgHE="
    
    # Try with bot's credentials first
    result = asyncio.run(test_session(session_str, 21216244, 'bb3649203a7c9e3adf27d5b906705ca0'))
    
    if not result:
        print("\nRetrying with original credentials from JSON...")
        asyncio.run(test_session(session_str, 2040, 'b18441a1ff607e10a989891a5462e627'))

