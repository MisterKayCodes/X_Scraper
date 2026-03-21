import sqlite3
from typing import Optional, Dict
from app.services.db_manager import db_path

def create_task(user_id: int, target_username: str) -> int:
    """
    Spawns a new harvest task in the database. Returns task_id.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (user_id, target_username, status) VALUES (?, ?, 'SCRAPING')",
        (user_id, target_username)
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def update_task_meta(task_id: int, total_items: int, msg_id: int):
    """
    Updates the task once the scraper finishes finding links.
    """
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE tasks SET total_items = ?, last_msg_id = ?, status = 'QUEUED' WHERE task_id = ?",
        (total_items, msg_id, task_id)
    )
    conn.commit()
    conn.close()

def log_processed_item(task_id: int, success: bool, size_kb: int = 0):
    """
    Granular update for the worker. Updates processed/success counts and storage.
    """
    conn = sqlite3.connect(db_path)
    if success:
        conn.execute(
            "UPDATE tasks SET processed_count = processed_count + 1, success_count = success_count + 1, storage_kb = storage_kb + ? WHERE task_id = ?",
            (size_kb, task_id)
        )
    else:
        conn.execute(
            "UPDATE tasks SET processed_count = processed_count + 1 WHERE task_id = ?",
            (task_id,)
        )
    conn.commit()
    conn.close()

def set_task_status(task_id: int, status: str):
    """
    Lifecycle control: SCRAPING, QUEUED, PAUSED, COMPLETED, STOPPED.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (status, task_id))
    conn.commit()
    conn.close()

def get_active_task(user_id: int) -> Optional[Dict]:
    """
    Returns the most recent non-completed task for a user.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM tasks WHERE user_id = ? AND status NOT IN ('COMPLETED', 'STOPPED') ORDER BY task_id DESC LIMIT 1",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_task_by_id(task_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_aggregated_stats(user_id: int) -> dict:
    """
    Returns global aggregated stats for the user across all tasks.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            COUNT(task_id) as total_tasks,
            SUM(total_items) as all_time_items,
            SUM(success_count) as all_time_success,
            SUM(storage_kb) as all_time_storage_kb
        FROM tasks 
        WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row['total_tasks'] > 0:
        return dict(row)
    return {
        'total_tasks': 0, 'all_time_items': 0, 
        'all_time_success': 0, 'all_time_storage_kb': 0
    }
