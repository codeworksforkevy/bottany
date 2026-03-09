from pathlib import Path
from .db import get_pool


async def init_database():

    pool = get_pool()

    schema_path = Path(__file__).parent / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    async with pool.acquire() as conn:
        await conn.execute(schema_sql)
