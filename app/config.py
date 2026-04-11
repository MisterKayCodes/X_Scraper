import os
import socket
import urllib3.util.connection as urllib3_cn
from dotenv import load_dotenv

# Fix Python requests 15-second DNS IPv6 timeout on Windows
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

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

# API Configuration
API_KEY = os.getenv("API_KEY", "mister_secret_key_2026")
API_PORT = int(os.getenv("API_PORT", 8001))

# Storage
DOWNLOAD_DIR = "downloads"
COOKIE_FILE = os.path.join("app", "data", "cookies.txt")

