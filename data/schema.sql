CREATE TABLE IF NOT EXISTS stream_snapshots (
    id SERIAL PRIMARY KEY,
    user_login TEXT NOT NULL,
    viewer_count INT,
    title TEXT,
    game_name TEXT,
    started_at TIMESTAMP,
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stream_user_time
ON stream_snapshots(user_login, recorded_at DESC);
