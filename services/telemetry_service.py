import os
import asyncpg
from datetime import datetime
from typing import Optional


class TelemetryService:

    def __init__(self):
        self.dsn = os.getenv("DATABASE_URL")
        self.pool: Optional[asyncpg.Pool] = None

        if not self.dsn:
            raise RuntimeError("DATABASE_URL not set.")

    async def init(self):
        if self.pool:
            return

        self.pool = await asyncpg.create_pool(
            dsn=self.dsn,
            min_size=1,
            max_size=5
        )

        await self._run_migrations()

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def _run_migrations(self):
        async with self.pool.acquire() as conn:

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS stream_snapshots (
                id SERIAL PRIMARY KEY,
                user_login TEXT,
                viewer_count INT,
                title TEXT,
                game_name TEXT,
                started_at TIMESTAMP,
                recorded_at TIMESTAMP DEFAULT NOW()
            );
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS stream_intelligence_history (
                id SERIAL PRIMARY KEY,
                user_login TEXT,
                volatility_score FLOAT,
                momentum INT,
                momentum_rate FLOAT,
                trend TEXT,
                health_score FLOAT,
                predicted_next FLOAT,
                recorded_at TIMESTAMP DEFAULT NOW()
            );
            """)

            await conn.execute("""
            CREATE TABLE IF NOT EXISTS drops_history (
                id SERIAL PRIMARY KEY,
                game_name TEXT,
                drops_active BOOLEAN,
                recorded_at TIMESTAMP DEFAULT NOW()
            );
            """)

    # ---------------- SNAPSHOT ----------------

    async def log_stream_snapshot(self, user_login, viewer_count, title, game_name, started_at=None):

        parsed_started_at = None
        if started_at:
            try:
                parsed_started_at = datetime.strptime(started_at, "%Y-%m-%dT%H:%M:%SZ")
            except:
                pass

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO stream_snapshots
                (user_login, viewer_count, title, game_name, started_at, recorded_at)
                VALUES ($1,$2,$3,$4,$5,$6)
            """,
            user_login, viewer_count, title, game_name,
            parsed_started_at, datetime.utcnow())

    async def get_recent_snapshots(self, user_login, limit=20):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT viewer_count, recorded_at
                FROM stream_snapshots
                WHERE user_login=$1
                ORDER BY recorded_at DESC
                LIMIT $2
            """, user_login, limit)

    # ---------------- INTELLIGENCE ----------------

    async def log_stream_intelligence(
        self,
        user_login,
        volatility_score,
        momentum,
        momentum_rate,
        trend,
        health_score,
        predicted_next
    ):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO stream_intelligence_history
                (user_login, volatility_score, momentum, momentum_rate, trend,
                 health_score, predicted_next, recorded_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            """,
            user_login,
            volatility_score,
            momentum,
            momentum_rate,
            trend,
            health_score,
            predicted_next,
            datetime.utcnow())

    async def get_health_history(self, user_login, limit=30):
        async with self.pool.acquire() as conn:
            return await conn.fetch("""
                SELECT health_score, recorded_at
                FROM stream_intelligence_history
                WHERE user_login=$1
                ORDER BY recorded_at DESC
                LIMIT $2
            """, user_login, limit)

    # ---------------- DROPS ----------------

    async def log_drops_state(self, game_name, drops_active):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO drops_history
                (game_name, drops_active, recorded_at)
                VALUES ($1,$2,$3)
            """, game_name, drops_active, datetime.utcnow())
