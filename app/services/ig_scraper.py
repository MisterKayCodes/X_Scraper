import asyncio
import instaloader
import glob
import os
from pathlib import Path
from app.data.db_manager import is_duplicate

def get_instaloader():
    """Initializes Instaloader and attempts to load an existing session cookie file."""
    L = instaloader.Instaloader(
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="",
        max_connection_attempts=1,  # CRITICAL: Fail fast. Do NOT wait 30 mins on 429!
        quiet=True                  # Suppress instaloader's own retry logs
    )
    # Search for any ig_session file in the root folder
    sessions = glob.glob("ig_session_*")
    if sessions:
        session_file = sessions[0]
        # Extracts username from the filename 'ig_session_username'
        username = session_file.replace("ig_session_", "")
        try:
            L.load_session_from_file(username, filename=session_file)
            print(f"[IG_SCRAPER] Authenticated via session: {session_file}")
        except Exception as e:
            print(f"[IG_SCRAPER] Failed to load session {session_file}: {e}")
    else:
        print("[IG_SCRAPER] No session found. Running unauthenticated (High Risk of 429).")
    
    return L

async def scrape_ig_profile_media(target_username: str, user_id: int, limit: int, status_callback=None):
    """
    Acts as the Producer: Checks an IG profile and extracts post shortcodes up to `limit`.
    Skips items already marked in the DB.
    """
    target_username = target_username.replace("@", "").replace("https://instagram.com/", "").replace("/", "")
    
    def fetch_shortcodes():
        L = get_instaloader()
        try:
            profile = instaloader.Profile.from_username(L.context, target_username)
        except Exception as e:
            return None, str(e)

        links = []
        count = 0
        try:
            # profile.get_posts() is a generator that fetches pages from Instagram
            for post in profile.get_posts():
                if count >= limit:
                    break
                
                shortcode = post.shortcode
                # We prefix with ig_ to distinguish from X tweets
                task_id_string = f"ig_{shortcode}"
                
                if not is_duplicate(task_id_string, user_id):
                    links.append(task_id_string)
                    count += 1
                    
        except Exception as e:
            # Return whatever we got before the error (likely a rate limit)
            return links, f"Partial scrape. Stopped due to: {e}"
            
        return links, None

    links, error = await asyncio.to_thread(fetch_shortcodes)
    
    if error and status_callback:
        if not links:
            await status_callback(f"❌ **IG Radar Failure:** {error}")
        else:
            await status_callback(f"⚠️ **Warning:** {error}")

    return links or []

async def download_ig_media(shortcode: str, download_dir: Path):
    """
    Acts as the Consumer: Downloads an IG post to the specified directory.
    Returns a list of local file paths and the caption.
    """
    def do_download():
        L = get_instaloader()
        # Set dirname pattern so it just drops files directly in the temp directory
        L.dirname_pattern = str(download_dir)
        try:
            post = instaloader.Post.from_shortcode(L.context, shortcode)
            caption = post.caption or f"Instagram Post: {shortcode}"
            
            # Instaloader will download images/videos. We must track what it creates.
            # We check what files exist before and after.
            before_files = set(download_dir.iterdir())
            L.download_post(post, target=shortcode)
            after_files = set(download_dir.iterdir())
            
            new_files = list(after_files - before_files)
            
            # Filter out JSONs or txt files that instaloader sometimes makes
            media_files = [f for f in new_files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.mp4']]
            
            return media_files, caption, None
        except Exception as e:
            return [], "", str(e)
            
    return await asyncio.to_thread(do_download)
