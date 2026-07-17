import asyncio
import yt_dlp
import re
from typing import Set

class YouTubeScraper:
    platform_name = "youtube"
    
    URL_PATTERNS = [r'youtube\.com', r'youtu\.be']
    CHANNEL_PATTERNS = [
        r'youtube\.com/channel/([^/\?]+)',
        r'youtube\.com/c/([^/\?]+)',
        r'youtube\.com/@([^/\?]+)',
        r'youtube\.com/user/([^/\?]+)',
    ]
    
    def detect_url(self, url: str) -> bool:
        return any(re.search(pattern, url) for pattern in self.URL_PATTERNS)
        
    async def get_channel_info(self, channel_url: str) -> dict:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlist_items': '0',
        }
        
        def extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(channel_url, download=False)
                    return {
                        'id': info.get('channel_id') or info.get('id'),
                        'name': info.get('channel') or info.get('uploader') or info.get('title'),
                        'url': info.get('channel_url') or channel_url,
                    }
                except Exception as e:
                    return {'error': str(e)}
        
        return await asyncio.get_event_loop().run_in_executor(None, extract)
        
    async def scrape_channel(self, channel_url: str, existing_ids: Set[str] = None, content_filter: str = 'all', limit: int = None) -> list:
        existing_ids = existing_ids or set()
        urls_to_scrape = []
        
        if content_filter in ('all', 'short', 'shorts'):
            urls_to_scrape.append(('short', channel_url.rstrip('/') + '/shorts'))
        
        if content_filter in ('all', 'video', 'videos'):
            urls_to_scrape.append(('video', channel_url.rstrip('/') + '/videos'))
            
        results = []
        for c_type, url in urls_to_scrape:
            items = await self._scrape_playlist(url, existing_ids, c_type)
            results.extend(items)
            if limit and len(results) >= limit:
                return results[:limit]
        return results

    async def _scrape_playlist(self, url: str, existing_ids: Set[str], content_type: str) -> list:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'ignoreerrors': True,
        }
        
        def get_entries():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    if info and 'entries' in info:
                        return list(info['entries'])
                    return []
                except Exception:
                    return []
        
        entries = await asyncio.get_event_loop().run_in_executor(None, get_entries)
        
        results = []
        for entry in entries:
            if not entry: continue
            video_id = entry.get('id')
            if not video_id or video_id in existing_ids: continue
            
            results.append({
                'content_id': video_id,
                'content_url': f"https://www.youtube.com/watch?v={video_id}",
                'title': entry.get('title'),
                'content_type': content_type
            })
        return results

youtube_scraper = YouTubeScraper()
