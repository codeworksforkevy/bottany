import sqlite3
from pathlib import Path

DB_PATH = Path("data/trivia_memory.db")


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS global_shown (
            entry_id TEXT PRIMARY KEY,
            shown_count INTEGER NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_history (
            user_id INTEGER NOT NULL,
            entry_id TEXT NOT NULL,
            PRIMARY KEY (user_id, entry_id)
        )
        """)

        conn.commit()


def get_global_count(entry_id: str) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT shown_count FROM global_shown WHERE entry_id=?",
            (entry_id,)
        )
        row = cur.fetchone()
        return row[0] if row else 0


def increment_global(entry_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO global_shown (entry_id, shown_count)
        VALUES (?, 1)
        ON CONFLICT(entry_id)
        DO UPDATE SET shown_count = shown_count + 1
        """, (entry_id,))

        conn.commit()


def user_has_seen(user_id: int, entry_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT 1 FROM user_history
        WHERE user_id=? AND entry_id=?
        """, (user_id, entry_id))
        return cur.fetchone() is not None


def mark_user_seen(user_id: int, entry_id: str):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()

        cur.execute("""
        INSERT OR IGNORE INTO user_history (user_id, entry_id)
        VALUES (?, ?)
        """, (user_id, entry_id))

        conn.commit()
