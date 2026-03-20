-- =================================================
-- PET A KITTEN TABLE
-- =================================================

CREATE TABLE IF NOT EXISTS kitten_pets (

    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,

    -- total pet count
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

    -- user-defined kitten name
    kitten_name TEXT NOT NULL,

    adopted_at TIMESTAMP DEFAULT NOW(),

    adoption_count INTEGER DEFAULT 1,

    -- allow multiple kittens per user
    PRIMARY KEY (guild_id, user_id, kitten_name)

);


-- =================================================
-- GLOBAL KITTEN EVENTS
-- =================================================

CREATE TABLE IF NOT EXISTS kitten_global_events (

    guild_id BIGINT PRIMARY KEY,

    -- current active global event text
    event_text TEXT,

    -- last time event was generated
    last_event TIMESTAMP,

    -- future systems (not used yet)
    civilization_level INTEGER DEFAULT 1,

    total_kittens INTEGER DEFAULT 0

);
