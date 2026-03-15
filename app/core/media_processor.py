import re

def sanitize_filename(text: str, max_length: int = 50) -> str:
    """
    Pure logic to clean text for use as a filename.
    """
    clean = re.sub(r'http\S+', '', text)
    clean = re.sub(r'[^\w\s-]', '', clean).strip()
    clean = re.sub(r'[-\s]+', '_', clean)
    return clean[:max_length] or "x_media"

def resolve_extension(media_type: str, url: str) -> str:
    """
    Pure logic to determine the file extension based on type and URL.
    """
    if "video" in media_type:
        return "mp4"
    
    ext = url.split('.')[-1].split('?')[0] if '.' in url else "jpg"
    if len(ext) > 4:
        ext = "jpg"
    return ext

def parse_media_list(data: dict) -> list:
    """
    Extracts a standardized list of media objects from raw API response.
    """
    media_list = data.get("media_extended", [])
    if not media_list:
        media_urls = data.get("mediaUrls", [])
        if media_urls:
            media_list = [{"url": u, "type": "image"} for u in media_urls]
    return media_list
