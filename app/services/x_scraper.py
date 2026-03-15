import requests
from app.config import HEADERS, VX_TWITTER_API
from app.core.media_processor import parse_media_list

def fetch_x_metadata(url: str):
    """
    Fetches post metadata from vxtwitter API.
    """
    # Convert to API link
    api_url = url.replace("https://x.com", VX_TWITTER_API)
    api_url = api_url.replace("https://twitter.com", VX_TWITTER_API)
    api_url = api_url.split('?')[0]

    try:
        response = requests.get(api_url, headers=HEADERS, timeout=20, verify=False)
        if response.status_code != 200:
            return None, f"Metadata unavailable (Status {response.status_code})"

        return response.json(), None
    except Exception as e:
        return None, str(e)
