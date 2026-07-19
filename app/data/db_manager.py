import sqlite3
import os
from pathlib import Path

# Ensure the data directory exists
data_dir = Path("app/data")
data_dir.mkdir(parents=True, exist_ok=True)
db_path = data_dir / "scraped_media.db"

def init_db():
    conn = sqlite3.connect(db_path)
    # Rule: Enable Write-Ahead Logging (WAL) for Multi-User Concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    # Seen Tweets Table (User-isolated history)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_tweets (
            tweet_id TEXT,
            user_id INTEGER,
            username TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (tweet_id, user_id)
        )
    """)
    
    # settings Table (User-isolated preferences)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER,
            key TEXT,
            value TEXT,
            PRIMARY KEY (user_id, key)
        )
    """)
    # tasks Table (Full lifecycle tracking)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            target_username TEXT,
            total_items INTEGER DEFAULT 0,
            processed_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'SCRAPING',
            storage_kb INTEGER DEFAULT 0,
            last_msg_id INTEGER,
            next_post_time INTEGER DEFAULT 0,
            media_filter TEXT DEFAULT 'any',
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Try adding the columns if table already exists
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN next_post_time INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE tasks ADD COLUMN media_filter TEXT DEFAULT 'any'")
    except sqlite3.OperationalError:
        pass

    
    # NEW TABLES FOR MULTI-CHANNEL & AUTO-CHECK LOGIC
    # Source channels (YouTube, X, etc.)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS source_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            channel_url TEXT NOT NULL,
            channel_name TEXT,
            collection_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, channel_url)
        )
    ''')
    
    # Scraped content (platform agnostic tracking)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS scraped_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_channel_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            content_url TEXT NOT NULL,
            content_id TEXT NOT NULL,
            title TEXT,
            description TEXT,
            content_type TEXT,
            duration INTEGER,
            file_size INTEGER,
            thumbnail_url TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_channel_id) REFERENCES source_channels(id),
            UNIQUE(source_channel_id, content_id)
        )
    ''')
    
    # Telegram destination channels
    conn.execute('''
        CREATE TABLE IF NOT EXISTS telegram_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            channel_id TEXT NOT NULL,
            channel_title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, channel_id)
        )
    ''')
    
    # Posted content - tracks what was posted where
    conn.execute('''
        CREATE TABLE IF NOT EXISTS posted_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scraped_content_id INTEGER NOT NULL,
            telegram_channel_id INTEGER NOT NULL,
            message_id INTEGER,
            posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'success',
            error_message TEXT,
            FOREIGN KEY (scraped_content_id) REFERENCES scraped_content(id),
            FOREIGN KEY (telegram_channel_id) REFERENCES telegram_channels(id),
            UNIQUE(scraped_content_id, telegram_channel_id)
        )
    ''')
    
    # Auto-check table for interval logic
    conn.execute('''
        CREATE TABLE IF NOT EXISTS auto_check (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source_channel_id INTEGER NOT NULL,
            telegram_channel_id INTEGER NOT NULL,
            filter_mode TEXT DEFAULT 'all',
            interval_minutes INTEGER DEFAULT 5,
            is_active INTEGER DEFAULT 0,
            is_running INTEGER DEFAULT 0,
            last_check TIMESTAMP,
            next_check TIMESTAMP,
            last_new_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_channel_id) REFERENCES source_channels(id),
            FOREIGN KEY (telegram_channel_id) REFERENCES telegram_channels(id),
            UNIQUE(source_channel_id, telegram_channel_id)
        )
    ''')

    # NEW TABLE: saved_targets (For manual quick harvest CRUD)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS saved_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            target_username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, platform, target_username)
        )
    ''')
    
    # 🔁 GLOBAL MIGRATION: Ensure all tables match the Enterprise Blueprint
    cursor = conn.cursor()
    
    # 1. Migrate settings
    cursor.execute("PRAGMA table_info(settings)")
    cols = [r[1] for r in cursor.fetchall()]
    if "user_id" not in cols:
        print("[MIGRATION] Upgrading settings to Multi-User...")
        conn.execute("ALTER TABLE settings ADD COLUMN user_id INTEGER DEFAULT 0")
    
    # 2. Migrate seen_tweets
    cursor.execute("PRAGMA table_info(seen_tweets)")
    cols = [r[1] for r in cursor.fetchall()]
    if "user_id" not in cols:
        print("[MIGRATION] Upgrading seen_tweets to Multi-User...")
        conn.execute("ALTER TABLE seen_tweets ADD COLUMN user_id INTEGER DEFAULT 0")

    # Migration: Add storage_kb and last_msg_id to tasks if missing (Safety)
    cursor.execute("PRAGMA table_info(tasks)")
    cols = [r[1] for r in cursor.fetchall()]
    if "storage_kb" not in cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN storage_kb INTEGER DEFAULT 0")
    if "last_msg_id" not in cols:
        conn.execute("ALTER TABLE tasks ADD COLUMN last_msg_id INTEGER")

    conn.commit()
    conn.close()

def is_duplicate(tweet_id: str, user_id: int) -> bool:
    """
    Returns True if we've seen this tweet_id before for this user.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen_tweets WHERE tweet_id = ? AND user_id = ?", (tweet_id, user_id))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_as_seen(tweet_id: str, user_id: int, username: str):
    """
    Records a tweet_id in the vault after successful processing.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO seen_tweets (tweet_id, user_id, username) VALUES (?, ?, ?)", 
            (tweet_id, user_id, username)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass # Already exists
    finally:
        conn.close()

def set_task_next_post_time(task_id: int, next_time: int):
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE tasks SET next_post_time = ? WHERE task_id = ?", (next_time, task_id))
    conn.commit()
    conn.close()

def set_setting(user_id: int, key: str, value: str):
    """
    Persist a user-specific setting value.
    """
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT OR REPLACE INTO settings (user_id, key, value) VALUES (?, ?, ?)", 
        (user_id, key, str(value))
    )
    conn.commit()
    conn.close()

def get_setting(user_id: int, key: str, default=None):
    """
    Retrieve a user-specific setting value.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE user_id = ? AND key = ?", (user_id, key))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def add_saved_target(user_id: int, platform: str, target_username: str) -> bool:
    """Adds a new saved target for the user. Returns True if added, False if duplicate."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO saved_targets (user_id, platform, target_username) VALUES (?, ?, ?)",
            (user_id, platform, target_username)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_saved_targets(user_id: int, platform: str = None) -> list:
    """Gets saved targets for a user, optionally filtered by platform."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if platform:
        cursor.execute("SELECT id, platform, target_username FROM saved_targets WHERE user_id = ? AND platform = ? ORDER BY id", (user_id, platform))
    else:
        cursor.execute("SELECT id, platform, target_username FROM saved_targets WHERE user_id = ? ORDER BY platform, id", (user_id,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def delete_saved_target(target_id: int, user_id: int):
    """Deletes a saved target."""
    conn = sqlite3.connect(db_path)
    conn.execute("DELETE FROM saved_targets WHERE id = ? AND user_id = ?", (target_id, user_id))
    conn.commit()
    conn.close()

from typing import Optional, Dict
from app.data.db_task_layer import (
    create_task, update_task_meta, log_processed_item,
    set_task_status, get_active_task, get_task_by_id,
    get_user_aggregated_stats
)
