CREATE TABLE IF NOT EXISTS kitten_pets (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    pet_count INTEGER NOT NULL DEFAULT 0,
    tier TEXT,
    PRIMARY KEY (guild_id, user_id)
);
