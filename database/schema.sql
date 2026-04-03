-- =============================================================================
-- schema.sql
-- Full database schema for Bottany bot
-- Run once on a fresh database, or re-run safely (all statements are idempotent)
-- =============================================================================


-- =============================================================================
-- ANIME & ANIMATION AWARDS
-- =============================================================================

CREATE TABLE IF NOT EXISTS anime_awards (

    id                   SERIAL PRIMARY KEY,

    -- Titles
    title_en             TEXT NOT NULL,
    title_jp             TEXT NOT NULL DEFAULT '',
    title_display        TEXT NOT NULL,

    -- Core
    year                 INT  NOT NULL,
    era                  TEXT CHECK (era IN ('classic', 'modern')),

    -- Award
    award_show_id        TEXT NOT NULL,
    award_name           TEXT NOT NULL,
    category             TEXT,
    award_type           TEXT CHECK (
                             award_type IN ('feature', 'grand_prize', 'jury', 'special', 'screening')
                         ),
    jp_label             TEXT,

    -- Credits
    directors            TEXT[]   DEFAULT ARRAY[]::TEXT[],
    studios              TEXT[]   DEFAULT ARRAY[]::TEXT[],
    productions          TEXT[]   DEFAULT ARRAY[]::TEXT[],

    -- Technical
    animation_technique  TEXT,
    format               TEXT,

    -- Media
    thumbnail            TEXT,

    -- Links
    official_link        TEXT,
    imdb_link            TEXT,
    mal_link             TEXT,

    -- Meta
    sources              TEXT[]   DEFAULT ARRAY[]::TEXT[],
    confidence           TEXT CHECK (confidence IN ('high', 'medium', 'low'))
                         DEFAULT 'medium',

    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP

);

CREATE INDEX IF NOT EXISTS idx_anime_year      ON anime_awards (year);
CREATE INDEX IF NOT EXISTS idx_anime_show      ON anime_awards (award_show_id);
CREATE INDEX IF NOT EXISTS idx_anime_type      ON anime_awards (award_type);
CREATE INDEX IF NOT EXISTS idx_anime_era       ON anime_awards (era);
CREATE INDEX IF NOT EXISTS idx_anime_directors ON anime_awards USING GIN (directors);
CREATE INDEX IF NOT EXISTS idx_anime_studios   ON anime_awards USING GIN (studios);


-- =============================================================================
-- KITTEN — PET INTERACTIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS kitten_pets (

    guild_id             BIGINT  NOT NULL,
    user_id              BIGINT  NOT NULL,

    pet_count            INTEGER NOT NULL DEFAULT 0,
    tier                 TEXT,
    achievements         TEXT[]  DEFAULT ARRAY[]::TEXT[],

    PRIMARY KEY (guild_id, user_id)

);


-- =============================================================================
-- KITTEN — ADOPTIONS
-- =============================================================================

CREATE TABLE IF NOT EXISTS kitten_adoptions (

    guild_id             BIGINT  NOT NULL,
    user_id              BIGINT  NOT NULL,
    kitten_name          TEXT    NOT NULL,

    adopted_at           TIMESTAMP DEFAULT NOW(),
    adoption_count       INTEGER   DEFAULT 1,

    PRIMARY KEY (guild_id, user_id, kitten_name)

);


-- =============================================================================
-- KITTEN — GLOBAL EVENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS kitten_global_events (

    guild_id             BIGINT PRIMARY KEY,

    event_text           TEXT,
    last_event           TIMESTAMP,

    civilization_level   INTEGER DEFAULT 1,
    total_kittens        INTEGER DEFAULT 0

);
