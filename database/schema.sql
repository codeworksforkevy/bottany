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


-- =================================================
-- KITTEN ADOPTION TABLE
-- =================================================

CREATE TABLE IF NOT EXISTS kitten_adoptions (

    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,

    -- kitten name given by user
    kitten_name TEXT NOT NULL,

    -- adoption timestamp
    adopted_at TIMESTAMP DEFAULT NOW(),

    -- allows future multi-adoption systems
    adoption_count INTEGER DEFAULT 1,

    PRIMARY KEY (guild_id, user_id)

);
