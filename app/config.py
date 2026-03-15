import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Browser Mimicry Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://x.com/',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}

# API URLs
VX_TWITTER_API = "http://api.vxtwitter.com"

# Telegram Configuration (To be filled by user)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "REPLACE_ME")

# Storage
DOWNLOAD_DIR = "downloads"
COOKIE_FILE = os.path.join("app", "data", "cookies.txt")
