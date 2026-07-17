import sqlite3
import asyncio
from datetime import datetime
from functools import partial
from pathlib import Path

# Connect to X Scraper's DB
data_dir = Path("app/data")
db_path = data_dir / "scraped_media.db"

def get_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Async wrapper for running sync db operations
async def run_sync(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))

def _add_source_channel(user_id: int, platform: str, channel_url: str, channel_name: str, collection_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO source_channels (user_id, platform, channel_url, channel_name, collection_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, platform, channel_url, channel_name, collection_name))
        conn.commit()
        channel_id = cursor.lastrowid
        conn.close()
        return channel_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def _get_user_source_channels(user_id: int, platform: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    if platform:
        cursor.execute('SELECT * FROM source_channels WHERE user_id = ? AND platform = ?', (user_id, platform))
    else:
        cursor.execute('SELECT * FROM source_channels WHERE user_id = ?', (user_id,))
    channels = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return channels

def _add_scraped_content(source_channel_id: int, platform: str, content_url: str, content_id: str, title: str = None, description: str = None, content_type: str = None, duration: int = None, file_size: int = None, thumbnail_url: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO scraped_content 
            (source_channel_id, platform, content_url, content_id, title, description, content_type, duration, file_size, thumbnail_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (source_channel_id, platform, content_url, content_id, title, description, content_type, duration, file_size, thumbnail_url))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return new_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def _content_exists(source_channel_id: int, content_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM scraped_content WHERE source_channel_id = ? AND content_id = ?', (source_channel_id, content_id))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def _get_existing_content_ids(source_channel_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT content_id FROM scraped_content WHERE source_channel_id = ?', (source_channel_id,))
    content_ids = {row['content_id'] for row in cursor.fetchall()}
    conn.close()
    return content_ids

def _get_source_channel_by_id(channel_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM source_channels WHERE id = ?', (channel_id,))
    channel = cursor.fetchone()
    conn.close()
    return dict(channel) if channel else None

def _add_telegram_channel(user_id: int, channel_id: str, channel_title: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO telegram_channels (user_id, channel_id, channel_title) VALUES (?, ?, ?)', (user_id, channel_id, channel_title))
        conn.commit()
        tg_channel_id = cursor.lastrowid
        conn.close()
        return tg_channel_id
    except sqlite3.IntegrityError:
        cursor.execute('SELECT id FROM telegram_channels WHERE user_id = ? AND channel_id = ?', (user_id, channel_id))
        existing = cursor.fetchone()
        conn.close()
        return existing['id'] if existing else None

def _get_user_telegram_channels(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM telegram_channels WHERE user_id = ?', (user_id,))
    channels = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return channels

def _add_posted_content(scraped_content_id: int, telegram_channel_id: int, message_id: int = None, status: str = 'success', error_message: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO posted_content (scraped_content_id, telegram_channel_id, message_id, status, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (scraped_content_id, telegram_channel_id, message_id, status, error_message))
        conn.commit()
        posted_id = cursor.lastrowid
        conn.close()
        return posted_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def _get_unposted_content(source_channel_id: int, telegram_channel_id: int, filter_mode: str = 'all'):
    conn = get_connection()
    cursor = conn.cursor()
    base_query = '''
        SELECT sc.* FROM scraped_content sc
        WHERE sc.source_channel_id = ?
        AND sc.id NOT IN (
            SELECT scraped_content_id FROM posted_content 
            WHERE telegram_channel_id = ? AND status = 'success'
        )
    '''
    if filter_mode == 'shorts':
        base_query += " AND sc.content_type = 'short'"
    elif filter_mode == 'videos':
        base_query += " AND sc.content_type = 'video'"
    
    base_query += ' ORDER BY sc.scraped_at'
    cursor.execute(base_query, (source_channel_id, telegram_channel_id))
    content = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return content

def _create_auto_check(user_id: int, source_channel_id: int, telegram_channel_id: int, filter_mode: str = 'all', interval_minutes: int = 5):
    conn = get_connection()
    cursor = conn.cursor()
    from datetime import timedelta
    next_check = datetime.now() + timedelta(minutes=interval_minutes)
    try:
        cursor.execute('''
            INSERT INTO auto_check (user_id, source_channel_id, telegram_channel_id, filter_mode, interval_minutes, is_active, next_check)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        ''', (user_id, source_channel_id, telegram_channel_id, filter_mode, interval_minutes, next_check.isoformat()))
        conn.commit()
        auto_id = cursor.lastrowid
        conn.close()
        return auto_id
    except sqlite3.IntegrityError:
        cursor.execute('''
            UPDATE auto_check SET is_active = 1, filter_mode = ?, interval_minutes = ?, next_check = ?
            WHERE source_channel_id = ? AND telegram_channel_id = ?
        ''', (filter_mode, interval_minutes, next_check.isoformat(), source_channel_id, telegram_channel_id))
        conn.commit()
        cursor.execute('SELECT id FROM auto_check WHERE source_channel_id = ? AND telegram_channel_id = ?', (source_channel_id, telegram_channel_id))
        existing = cursor.fetchone()
        conn.close()
        return existing['id'] if existing else None

def _get_active_auto_checks():
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute('''
        SELECT ac.*, sc.channel_url, sc.platform, sc.collection_name, sc.channel_name,
               tc.channel_id as tg_channel_id_str, tc.channel_title
        FROM auto_check ac
        JOIN source_channels sc ON ac.source_channel_id = sc.id
        JOIN telegram_channels tc ON ac.telegram_channel_id = tc.id
        WHERE ac.is_active = 1 AND ac.is_running = 0 AND (ac.next_check IS NULL OR ac.next_check <= ?)
    ''', (now,))
    checks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return checks

def _update_auto_check(auto_check_id: int, **kwargs):
    conn = get_connection()
    cursor = conn.cursor()
    set_clause = ', '.join([f'{k} = ?' for k in kwargs.keys()])
    values = list(kwargs.values()) + [auto_check_id]
    cursor.execute(f'UPDATE auto_check SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()

def _get_user_auto_checks(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ac.*, sc.collection_name, tc.channel_title
        FROM auto_check ac
        JOIN source_channels sc ON ac.source_channel_id = sc.id
        JOIN telegram_channels tc ON ac.telegram_channel_id = tc.id
        WHERE ac.user_id = ? AND ac.is_active = 1
    ''', (user_id,))
    checks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return checks

def _stop_auto_check(source_channel_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE auto_check SET is_active = 0, is_running = 0 WHERE source_channel_id = ?', (source_channel_id,))
    conn.commit()
    conn.close()

# Async wrappers
async def add_source_channel(*args, **kwargs): return await run_sync(_add_source_channel, *args, **kwargs)
async def get_user_source_channels(*args, **kwargs): return await run_sync(_get_user_source_channels, *args, **kwargs)
async def get_source_channel_by_id(*args, **kwargs): return await run_sync(_get_source_channel_by_id, *args, **kwargs)
async def add_scraped_content(*args, **kwargs): return await run_sync(_add_scraped_content, *args, **kwargs)
async def content_exists(*args, **kwargs): return await run_sync(_content_exists, *args, **kwargs)
async def get_existing_content_ids(*args, **kwargs): return await run_sync(_get_existing_content_ids, *args, **kwargs)
async def add_telegram_channel(*args, **kwargs): return await run_sync(_add_telegram_channel, *args, **kwargs)
async def get_user_telegram_channels(*args, **kwargs): return await run_sync(_get_user_telegram_channels, *args, **kwargs)
async def add_posted_content(*args, **kwargs): return await run_sync(_add_posted_content, *args, **kwargs)
async def get_unposted_content(*args, **kwargs): return await run_sync(_get_unposted_content, *args, **kwargs)
async def create_auto_check(*args, **kwargs): return await run_sync(_create_auto_check, *args, **kwargs)
async def get_active_auto_checks(*args, **kwargs): return await run_sync(_get_active_auto_checks, *args, **kwargs)
async def update_auto_check(*args, **kwargs): return await run_sync(_update_auto_check, *args, **kwargs)
async def get_user_auto_checks(*args, **kwargs): return await run_sync(_get_user_auto_checks, *args, **kwargs)
async def stop_auto_check(*args, **kwargs): return await run_sync(_stop_auto_check, *args, **kwargs)
