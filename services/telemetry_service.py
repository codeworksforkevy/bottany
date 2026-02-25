
import os
import asyncpg
from datetime import datetime
from typing import Optional


class TelemetryService:

    def __init__(self):
        self.dsn: Optional[str] = os.getenv("DATABASE_URL")
        self.pool: Optional[asyncpg.Pool] = None

        if not self.dsn:
            raise RuntimeError("DATABASE_URL environment variable is not set.")

    # -------------------------------------------------
    # INIT / CLOSE
    # -------------------------------------------------

    async def init(self):
        if self.pool is not None:
            return  # already initialized

        self.pool = await asyncpg.create_pool(
            dsn=self.dsn,
            min_size=1,
            max_size=5,
            command_timeout=30
        )

    async def close(self):
        if self.pool:
            await self.pool.close()

    # -------------------------------------------------
    # STREAM SNAPSHOT LOGGING
    # -------------------------------------------------

    async def log_stream_snapshot(
        self,
        user_login: str,
        viewer_count: int,
        title: str,
        game_name: str,
        started_at: Optional[str] = None
    ):
        """
        Insert a stream snapshot into PostgreSQL.
        """

        if not self.pool:
            raise RuntimeError("TelemetryService not initialized.")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO stream_snapshots
                (user_login, viewer_count, title, game_name, started_at, recorded_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                user_login,
                viewer_count,
                title,
                game_name,
                started_at,
                datetime.utcnow()
            )

    # -------------------------------------------------
    # FUTURE EXTENSIONS
    # -------------------------------------------------

    async def log_drops_state(
        self,
        game_name: str,
        drops_active: bool
    ):
        """
        Optional: future drops lifecycle logging
        """

        if not self.pool:
            raise RuntimeError("TelemetryService not initialized.")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO drops_history
                (game_name, drops_active, recorded_at)
                VALUES ($1, $2, $3)
                """,
                game_name,
                drops_active,
                datetime.utcnow()
            )

    async def get_recent_snapshots(
        self,
        user_login: str,
        limit: int = 10
    ):
        """
        Fetch recent stream snapshots (for anomaly detection / analytics).
        """

        if not self.pool:
            raise RuntimeError("TelemetryService not initialized.")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT viewer_count, recorded_at
                FROM stream_snapshots
                WHERE user_login = $1
                ORDER BY recorded_at DESC
                LIMIT $2
                """,
                user_login,
                limit
            )

        return rows
