import os
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")

DECAY_LAMBDA = 0.3      # entry-level weekly decay
FIELD_DECAY_LAMBDA = 0.25  # field-level weekly decay
COLD_START_BOOST = 2.0


# -------------------------------------------------
# INIT DB
# -------------------------------------------------
def init_db():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set.")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            # Entry-level tracking
            cur.execute("""
            CREATE TABLE IF NOT EXISTS global_shown (
                entry_id TEXT PRIMARY KEY,
                score DOUBLE PRECISION NOT NULL DEFAULT 0,
                last_updated TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """)

            # User history
            cur.execute("""
            CREATE TABLE IF NOT EXISTS user_history (
                user_id BIGINT NOT NULL,
                entry_id TEXT NOT NULL,
                PRIMARY KEY (user_id, entry_id)
            );
            """)

            # Field-level entropy tracking
            cur.execute("""
            CREATE TABLE IF NOT EXISTS field_stats (
                field TEXT PRIMARY KEY,
                score DOUBLE PRECISION NOT NULL DEFAULT 0,
                last_updated TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """)

        conn.commit()


# -------------------------------------------------
# WEIGHTED SELECT WITH:
# - Weekly decay
# - Cold start boost
# - Field entropy balancing
# -------------------------------------------------
def weighted_select(entries, user_id, k=25):
    """
    entries = list of dict:
        {
            "id": "...",
            "field": "..."
        }
    """

    if not entries:
        return []

    entry_ids = [e["id"] for e in entries]
    entry_fields = {e["id"]: e.get("field") for e in entries}

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            cur.execute(f"""
            WITH candidates AS (
                SELECT
                    e.entry_id,

                    COALESCE(g.score, 0) AS entry_score,
                    COALESCE(
                        EXTRACT(EPOCH FROM (NOW() - g.last_updated)) / 604800,
                        0
                    ) AS entry_weeks,

                    COALESCE(f.score, 0) AS field_score,
                    COALESCE(
                        EXTRACT(EPOCH FROM (NOW() - f.last_updated)) / 604800,
                        0
                    ) AS field_weeks,

                    CASE
                        WHEN g.entry_id IS NULL THEN {COLD_START_BOOST}
                        ELSE 1.0
                    END AS cold_boost,

                    CASE
                        WHEN u.entry_id IS NULL THEN 1
                        ELSE 0.3
                    END AS user_factor

                FROM unnest(%s::text[]) AS e(entry_id)

                LEFT JOIN global_shown g
                    ON g.entry_id = e.entry_id

                LEFT JOIN user_history u
                    ON u.entry_id = e.entry_id
                    AND u.user_id = %s

                LEFT JOIN field_stats f
                    ON f.field = (
                        SELECT field
                        FROM (
                            SELECT unnest(%s::text[]) AS entry_id,
                                   unnest(%s::text[]) AS field
                        ) AS mapping
                        WHERE mapping.entry_id = e.entry_id
                        LIMIT 1
                    )
            )

            SELECT entry_id
            FROM candidates
            ORDER BY RANDOM()
                * (
                    1.0 /
                    (
                        1 + (
                            entry_score
                            * exp(-{DECAY_LAMBDA} * entry_weeks)
                        )
                    )
                )
                * (
                    1.0 /
                    (
                        1 + (
                            field_score
                            * exp(-{FIELD_DECAY_LAMBDA} * field_weeks)
                        )
                    )
                )
                * cold_boost
                * user_factor
            DESC
            LIMIT %s;
            """, (
                entry_ids,
                user_id,
                entry_ids,
                [entry_fields[eid] for eid in entry_ids],
                k
            ))

            rows = cur.fetchall()
            selected_ids = [r[0] for r in rows]

            # ---- Update entry + field stats ----
            for entry_id in selected_ids:
                field = entry_fields.get(entry_id)

                # Entry update
                cur.execute("""
                INSERT INTO global_shown (entry_id, score, last_updated)
                VALUES (%s, 1, NOW())
                ON CONFLICT (entry_id)
                DO UPDATE SET
                    score = global_shown.score + 1,
                    last_updated = NOW();
                """, (entry_id,))

                # User history update
                cur.execute("""
                INSERT INTO user_history (user_id, entry_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
                """, (user_id, entry_id))

                # Field update
                if field:
                    cur.execute("""
                    INSERT INTO field_stats (field, score, last_updated)
                    VALUES (%s, 1, NOW())
                    ON CONFLICT (field)
                    DO UPDATE SET
                        score = field_stats.score + 1,
                        last_updated = NOW();
                    """, (field,))

        conn.commit()

    return selected_ids


# -------------------------------------------------
# STATS
# -------------------------------------------------
def stats():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:

            cur.execute("SELECT COUNT(*) FROM global_shown;")
            tracked = cur.fetchone()[0]

            cur.execute("SELECT SUM(score) FROM global_shown;")
            total_score = cur.fetchone()[0] or 0

            cur.execute("""
            SELECT field, score
            FROM field_stats
            ORDER BY score DESC
            LIMIT 5;
            """)
            top_fields = cur.fetchall()

    return {
        "tracked_entries": tracked,
        "total_score": total_score,
        "top_fields": top_fields
    }
