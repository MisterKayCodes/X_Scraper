import asyncio
import re
import yt_dlp
from pathlib import Path
from typing import Set, Optional

# Always resolve cookies relative to the project root (two levels up from app/services/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_COOKIES_PATH = _PROJECT_ROOT / 'youtube_cookies.txt'


def _format_count(n) -> str:
    """Format a large number into a human readable string."""
    if not n:
        return 'N/A'
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def _format_duration(seconds) -> str:
    """Format seconds into a human readable duration string."""
    if not seconds:
        return 'Unknown'
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


class YouTubeScraper:
    platform_name = "youtube"

    CHANNEL_PATTERNS = [
        r'youtube\.com/channel/([^/\?]+)',
        r'youtube\.com/c/([^/\?]+)',
        r'youtube\.com/@([^/\?]+)',
        r'youtube\.com/user/([^/\?]+)',
    ]

    def classify_url(self, url: str) -> str:
        """
        Classify a YouTube URL.
        Returns: 'single_video', 'shorts_video', 'channel', or 'unknown'
        """
        if re.search(r'youtube\.com/shorts/[a-zA-Z0-9_-]+', url):
            return 'shorts_video'
        if re.search(r'youtube\.com/watch\?v=', url) or re.search(r'youtu\.be/[a-zA-Z0-9_-]{6,}', url):
            return 'single_video'
        if any(re.search(p, url) for p in self.CHANNEL_PATTERNS):
            return 'channel'
        return 'unknown'

    async def get_channel_info(self, channel_url: str) -> dict:
        """
        Fetch rich channel metadata: name, handle, subscriber count, video count, shorts count.
        Returns error key if channel not found.
        """
        base_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'playlist_items': '0',
            'extractor_args': {'youtube': ['player_client=android,mweb']},
        }
        import os
        if _COOKIES_PATH.exists():
            base_opts['cookiefile'] = str(_COOKIES_PATH)
        count_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'ignoreerrors': True,
            'extractor_args': {'youtube': ['player_client=android,mweb']},
        }
        if _COOKIES_PATH.exists():
            count_opts['cookiefile'] = str(_COOKIES_PATH)

        def extract_meta():
            with yt_dlp.YoutubeDL(base_opts) as ydl:
                try:
                    info = ydl.extract_info(channel_url, download=False)
                    if not info:
                        return {'error': 'Could not find channel. Check the URL.'}
                    subs = info.get('channel_follower_count')
                    handle = info.get('uploader_id') or ''
                    if handle and not handle.startswith('@'):
                        handle = '@' + handle
                    return {
                        'id': info.get('channel_id') or info.get('id'),
                        'name': info.get('channel') or info.get('uploader') or info.get('title', 'Unknown'),
                        'handle': handle,
                        'url': info.get('channel_url') or channel_url,
                        'subscriber_count': subs,
                        'subscriber_count_formatted': _format_count(subs),
                    }
                except Exception as e:
                    return {'error': str(e)}

        def count_playlist(tab_url: str) -> int:
            with yt_dlp.YoutubeDL(count_opts) as ydl:
                try:
                    info = ydl.extract_info(tab_url, download=False)
                    if not info:
                        return 0
                    entries = info.get('entries', [])
                    # playlist_count is often absent for tab playlists, so always count entries
                    return len([e for e in entries if e is not None])
                except Exception:
                    return 0

        loop = asyncio.get_event_loop()
        base_url = channel_url.rstrip('/')

        # Step 1: Validate channel exists
        meta = await loop.run_in_executor(None, extract_meta)
        if 'error' in meta:
            return meta

        # Step 2: Count videos & shorts in parallel
        video_count, shorts_count = await asyncio.gather(
            loop.run_in_executor(None, count_playlist, base_url + '/videos'),
            loop.run_in_executor(None, count_playlist, base_url + '/shorts'),
        )

        meta['video_count'] = video_count
        meta['shorts_count'] = shorts_count
        return meta

    async def get_video_info(self, video_url: str) -> Optional[dict]:
        """
        Get single video metadata: title, duration, thumbnail.
        Used for single-video auto-detection preview.
        """
        opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extractor_args': {'youtube': ['player_client=android,mweb']},
        }
        if _COOKIES_PATH.exists():
            opts['cookiefile'] = str(_COOKIES_PATH)

        def extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                try:
                    info = ydl.extract_info(video_url, download=False)
                    if not info:
                        return None
                    dur = info.get('duration', 0)
                    return {
                        'id': info.get('id'),
                        'title': info.get('title', 'Unknown'),
                        'duration': dur,
                        'duration_formatted': _format_duration(dur),
                        'thumbnail': info.get('thumbnail'),
                        'channel': info.get('channel', ''),
                        'view_count': _format_count(info.get('view_count', 0)),
                    }
                except Exception as e:
                    return {'error': str(e)}

        return await asyncio.get_event_loop().run_in_executor(None, extract)

    async def get_video_duration(self, video_url: str) -> Optional[int]:
        """Lightweight duration-only check. Returns seconds or None."""
        info = await self.get_video_info(video_url)
        if info and not info.get('error'):
            return info.get('duration')
        return None

    async def scrape_channel(
        self,
        channel_url: str,
        existing_ids: Set[str] = None,
        content_filter: str = 'all',
        limit: int = None,
    ) -> list:
        """
        Scrape a YouTube channel for new content.
        Returns list of items ordered newest-first (YouTube's default).
        """
        existing_ids = existing_ids or set()
        urls_to_scrape = []

        if content_filter in ('all', 'short', 'shorts'):
            urls_to_scrape.append(('shorts', channel_url.rstrip('/') + '/shorts'))
        if content_filter in ('all', 'video', 'videos'):
            urls_to_scrape.append(('videos', channel_url.rstrip('/') + '/videos'))

        results = []
        for content_type, url in urls_to_scrape:
            items = await self._scrape_playlist(url, existing_ids, content_type, limit)
            results.extend(items)
            if limit and len(results) >= limit:
                return results[:limit]
        return results

    async def _scrape_playlist(
        self,
        url: str,
        existing_ids: Set[str],
        content_type: str,
        limit: int = None,
    ) -> list:
        """Fetch playlist entries with extract_flat (fast, no download)."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'ignoreerrors': True,
            'extractor_args': {'youtube': ['player_client=android,mweb']},
        }
        if _COOKIES_PATH.exists():
            ydl_opts['cookiefile'] = str(_COOKIES_PATH)
        if limit:
            ydl_opts['playlistend'] = limit * 2  # Fetch extra to account for deduplication

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
            if not entry:
                continue
            video_id = entry.get('id')
            if not video_id or video_id in existing_ids:
                continue
            results.append({
                'content_id': video_id,
                'content_url': f"https://www.youtube.com/watch?v={video_id}",
                'title': entry.get('title'),
                'content_type': content_type,
                'duration': entry.get('duration'),  # May be None in extract_flat mode
            })
        return results


youtube_scraper = YouTubeScraper()
