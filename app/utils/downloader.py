import requests
from pathlib import Path
from tqdm import tqdm
import sys
import yt_dlp
import os
import asyncio

# Always resolve cookies relative to the project root (two levels up from app/utils/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_COOKIES_PATH = _PROJECT_ROOT / 'youtube_cookies.txt'

def log(msg, level="INFO", quiet=False):
    if not quiet:
        print(f"[{level}] {msg}")
        sys.stdout.flush()

def download_file(url: str, dest_path: Path, headers: dict, quiet=False):
    """
    Download a file with progress bar and atomic writing (128KB buffer).
    """
    if dest_path.exists():
        log(f"Skipping: {dest_path.name} (already exists)", quiet=quiet)
        return True

    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    
    # Rule 12: Handle errors explicitly
    try:
        # Rule 14: Security - Verify is TRUE, 15s timeout
        with requests.get(url, headers=headers, stream=True, timeout=15, verify=True) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            desc = dest_path.name[:25]
            pbar = tqdm(
                total=total_size, 
                unit='B', 
                unit_scale=True, 
                desc=f"Downloading {desc}", 
                disable=quiet,
                leave=False
            )
            
            # Rule 4 & 8: 128KB is the "Senior" sweet spot for speed/stability
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=131072):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            pbar.close()
            temp_path.rename(dest_path)
            return True

    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"[🚨] Critical Download Failure: {e}")
        log(f"Download failed for {url}: {e}", "ERROR", quiet=quiet)
        return False

async def check_file_size(content_url: str, max_size_mb: int = 50, max_duration_seconds: int = None) -> dict:
    """Pre-flight check to get video size and ensure it's under limits."""
    max_bytes = max_size_mb * 1024 * 1024
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extractor_args': {'youtube': ['player_client=android']},
    }
    if _COOKIES_PATH.exists():
        ydl_opts['cookiefile'] = str(_COOKIES_PATH)
    
    def check():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(content_url, download=False)
                if not info:
                    return {'error': 'Could not get video info', 'exceeds_limit': False}
                
                filesize = info.get('filesize') or info.get('filesize_approx')
                
                if not filesize:
                    formats = info.get('formats', [])
                    for fmt in formats:
                        if fmt.get('ext') == 'mp4':
                            fs = fmt.get('filesize') or fmt.get('filesize_approx')
                            if fs:
                                filesize = fs
                                break
                
                exceeds_limit = False
                if filesize is not None:
                    exceeds_limit = filesize > max_bytes
                
                duration = info.get('duration', 0)
                exceeds_duration = False
                if max_duration_seconds and duration and duration > max_duration_seconds:
                    exceeds_duration = True

                return {
                    'filesize': filesize,
                    'filesize_mb': round(filesize / (1024 * 1024), 2) if filesize else None,
                    'duration': duration,
                    'exceeds_limit': exceeds_limit,
                    'exceeds_duration': exceeds_duration,
                    'size_unknown': filesize is None,
                    'title': info.get('title', '')
                }
            except Exception as e:
                return {'error': str(e), 'exceeds_limit': False}
    
    return await asyncio.get_event_loop().run_in_executor(None, check)

async def download_with_ytdlp(url: str, download_dir: Path, check_size_first: bool = True, max_duration_seconds: int = None) -> dict:
    """
    Downloads and remuxes video using yt-dlp to ensure Telegram thumbnails work.
    """
    if check_size_first or max_duration_seconds:
        size_info = await check_file_size(url, max_duration_seconds=max_duration_seconds)
        if size_info and size_info.get('exceeds_limit'):
            return {
                'success': False, 
                'error': f"File size ({size_info.get('filesize_mb', '?')}MB) exceeds 50MB limit."
            }
        if size_info and size_info.get('exceeds_duration'):
            duration = size_info.get('duration', 0)
            return {
                'success': False,
                'error': f"Video duration ({duration//60}m) exceeds limit ({max_duration_seconds//60}m)."
            }
            
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4][filesize<50M]/best[ext=mp4]/best',
        'outtmpl': str(download_dir / '%(id)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'extractor_args': {'youtube': ['player_client=android']},
    }
    if _COOKIES_PATH.exists():
        ydl_opts['cookiefile'] = str(_COOKIES_PATH)
    
    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                if info:
                    video_id = info.get('id')
                    ext = info.get('ext', 'mp4')
                    file_path = download_dir / f"{video_id}.{ext}"
                    
                    if file_path.exists():
                        file_size = file_path.stat().st_size
                        if file_size > 50 * 1024 * 1024:
                            file_path.unlink()
                            return {'success': False, 'error': f"Downloaded file ({round(file_size/(1024*1024), 2)}MB) exceeds limit."}
                        return {
                            'success': True,
                            'file_path': file_path,
                            'title': info.get('title', ''),
                            'filesize_mb': round(file_size / (1024 * 1024), 2)
                        }
                return {'success': False, 'error': 'Unknown download failure.'}
            except Exception as e:
                return {'success': False, 'error': str(e)}
    
    return await asyncio.get_event_loop().run_in_executor(None, download)
