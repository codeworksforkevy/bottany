CREATE TABLE IF NOT EXISTS kitten_pets (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    pet_count INTEGER DEFAULT 0,
    tier TEXT DEFAULT 'None',
    PRIMARY KEY (guild_id, user_id)
);
