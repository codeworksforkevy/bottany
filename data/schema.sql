CREATE TABLE IF NOT EXISTS stream_snapshots (
    id SERIAL PRIMARY KEY,
    user_login TEXT NOT NULL,
    viewer_count INT,
    title TEXT,
    game_name TEXT,
    started_at TIMESTAMP,
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drops_history (
    id SERIAL PRIMARY KEY,
    game_name TEXT,
    drops_active BOOLEAN,
    recorded_at TIMESTAMP DEFAULT NOW()
);
