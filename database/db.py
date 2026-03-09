import asyncpg
import os

pool: asyncpg.Pool | None = None


async def create_pool():
    global pool

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set")

    pool = await asyncpg.create_pool(
        database_url,
        min_size=1,
        max_size=10
    )

    return pool


def get_pool() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    return pool
