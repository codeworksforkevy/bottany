import os
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")


def init_db():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            cur.execute("""
            CREATE TABLE IF NOT EXISTS global_shown (
                entry_id TEXT PRIMARY KEY,
                shown_count INTEGER NOT NULL
            );
            """)

            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_history (
                user_id BIGINT NOT NULL,
                entry_id TEXT NOT NULL,
                PRIMARY KEY (user_id, entry_id)
            );
            """)

        conn.commit()


def get_global_count(entry_id: str) -> int:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT shown_count FROM global_shown WHERE entry_id=%s;",
                (entry_id,)
            )
            row = cur.fetchone()
            return row[0] if row else 0


def increment_global(entry_id: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO global_shown (entry_id, shown_count)
            VALUES (%s, 1)
            ON CONFLICT (entry_id)
            DO UPDATE SET shown_count = global_shown.shown_count + 1;
            """, (entry_id,))
        conn.commit()


def user_has_seen(user_id: int, entry_id: str) -> bool:
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT 1 FROM user_history
            WHERE user_id=%s AND entry_id=%s;
            """, (user_id, entry_id))
            return cur.fetchone() is not None


def mark_user_seen(user_id: int, entry_id: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            INSERT INTO user_history (user_id, entry_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING;
            """, (user_id, entry_id))
        conn.commit()
