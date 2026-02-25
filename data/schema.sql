
CREATE TABLE IF NOT EXISTS stream_snapshots (
    id SERIAL PRIMARY KEY,
    user_login TEXT,
    viewer_count INT,
    title TEXT,
    game_name TEXT,
    recorded_at TIMESTAMP DEFAULT NOW()
);
