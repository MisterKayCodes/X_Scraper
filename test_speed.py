import time
from app.services.x_scraper import fetch_x_metadata
from app.core.media_processor import parse_media_list, sanitize_filename, resolve_extension
from app.utils.downloader import download_file
from app.config import HEADERS, DOWNLOAD_DIR
from pathlib import Path

def test_speed():
    url = "https://x.com/MisterKayCodes/status/2034034921983914043"
    print(f"Testing URL: {url}")
    
    start_time = time.time()
    
    # 1. Fetch Metadata
    meta_start = time.time()
    data, error = fetch_x_metadata(url)
    if error:
        print(f"Error fetching metadata: {error}")
        return
    print(f"[+] Metadata fetched in {time.time() - meta_start:.2f}s")
    
    # 2. Extract Caption
    caption = data.get("text", "x_media")
    print(f"\n--- CAPTION EXTRACTED ---")
    print(caption)
    print("-------------------------\n")
    
    # 3. Process Media
    safe_name = sanitize_filename(caption)
    media_list = parse_media_list(data)
    
    if not media_list:
        print("No media found.")
        return
        
    print(f"Found {len(media_list)} media items.")
    
    download_path = Path(DOWNLOAD_DIR)
    download_path.mkdir(exist_ok=True)
    
    for i, item in enumerate(media_list):
        m_url = item.get("url")
        m_type = item.get("type", "image")
        ext = resolve_extension(m_type, m_url)
        
        filename = f"{safe_name}_{i}.{ext}" if len(media_list) > 1 else f"{safe_name}.{ext}"
        final_path = download_path / filename
        
        print(f"Downloading item {i+1} ({m_type})...")
        dl_start = time.time()
        success = download_file(m_url, final_path, HEADERS, quiet=True)
        if success:
            print(f"[+] Item {i+1} downloaded in {time.time() - dl_start:.2f}s")
            
            # Format like Telegram would
            media_caption = f"{caption}\n\n🎥 Item {i+1}" if len(media_list) > 1 else caption
            print(f"Final Telegram Caption length: {len(media_caption)} chars")
        else:
            print(f"[-] Failed to download item {i+1}")
            
    total_time = time.time() - start_time
    print(f"\n=== TOTAL TIME: {total_time:.2f} seconds ===")

if __name__ == "__main__":
    test_speed()
