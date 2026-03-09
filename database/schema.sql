-- =================================================
-- PET A KITTEN TABLE
-- =================================================

CREATE TABLE IF NOT EXISTS kitten_pets (

    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,

    -- how many times the user used /petakitten
    pet_count INTEGER NOT NULL DEFAULT 0,

    -- tier name
    tier TEXT,

    -- unlocked achievements
    achievements TEXT[] DEFAULT ARRAY[]::TEXT[],

    PRIMARY KEY (guild_id, user_id)

);
