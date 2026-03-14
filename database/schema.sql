-- =================================================
-- PET A KITTEN TABLE
-- =================================================

CREATE TABLE IF NOT EXISTS kitten_pets (

    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,

    pet_count INTEGER NOT NULL DEFAULT 0,

    tier TEXT,

    achievements TEXT[] DEFAULT ARRAY[]::TEXT[],

    PRIMARY KEY (guild_id, user_id)

);


-- =================================================
-- KITTEN ADOPTION TABLE
-- =================================================

CREATE TABLE IF NOT EXISTS kitten_adoptions (

    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,

    kitten_name TEXT NOT NULL,

    adopted_at TIMESTAMP DEFAULT NOW(),

    adoption_count INTEGER DEFAULT 1,

    PRIMARY KEY (guild_id, user_id, kitten_name)  -- <-- değişiklik burada

);


-- =================================================
-- GLOBAL KITTEN EVENTS
-- =================================================

CREATE TABLE IF NOT EXISTS kitten_global_events (

    guild_id BIGINT PRIMARY KEY,

    last_event TIMESTAMP,

    civilization_level INTEGER DEFAULT 1,

    total_kittens INTEGER DEFAULT 0

);
