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
            start_time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
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

from typing import Optional, Dict
from app.services.db_task_layer import (
    create_task, update_task_meta, log_processed_item,
    set_task_status, get_active_task, get_task_by_id,
    get_user_aggregated_stats
)
