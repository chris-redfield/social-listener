-- Social Listener Database Schema
-- This script runs automatically on first PostgreSQL container startup

-- ===================
-- LISTENERS TABLE
-- ===================
CREATE TABLE IF NOT EXISTS listeners (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    platform        VARCHAR(50) NOT NULL,       -- 'threads' | 'bluesky' | 'all'
    rule_type       VARCHAR(50) NOT NULL,       -- 'keyword' | 'mention' | 'hashtag'
    rule_value      VARCHAR(500) NOT NULL,      -- The actual keyword/handle to monitor
    is_active       BOOLEAN DEFAULT true,
    has_new_content BOOLEAN DEFAULT false,      -- Flag for "content captured"
    poll_frequency  INTEGER DEFAULT 300,        -- Seconds between polls
    last_polled_at  TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ===================
-- POSTS TABLE
-- ===================
CREATE TABLE IF NOT EXISTS posts (
    id                  SERIAL PRIMARY KEY,
    listener_id         INTEGER REFERENCES listeners(id) ON DELETE CASCADE,
    platform            VARCHAR(50) NOT NULL,       -- 'threads' | 'bluesky'
    platform_post_id    VARCHAR(255) NOT NULL,      -- Original post ID from platform
    author_handle       VARCHAR(255),
    author_display_name VARCHAR(255),
    author_avatar_url   TEXT,
    content             TEXT,
    post_url            TEXT,

    -- Engagement metrics
    likes_count         INTEGER DEFAULT 0,
    replies_count       INTEGER DEFAULT 0,
    reposts_count       INTEGER DEFAULT 0,
    quotes_count        INTEGER DEFAULT 0,
    views_count         INTEGER DEFAULT 0,
    shares_count        INTEGER DEFAULT 0,
    clicks_count        INTEGER DEFAULT 0,

    -- NLP Analysis results
    sentiment_score     FLOAT,                      -- -1.0 to 1.0
    sentiment_label     VARCHAR(50),                -- 'positive' | 'negative' | 'neutral'
    nlp_processed_at    TIMESTAMP,                  -- When NLP was run
    nlp_error           TEXT,                       -- Error message if NLP failed

    -- Timestamps
    post_created_at     TIMESTAMP,                  -- When post was made on platform
    collected_at        TIMESTAMP DEFAULT NOW(),    -- When we collected it

    CONSTRAINT uq_platform_post UNIQUE(platform, platform_post_id)
);

-- ===================
-- ENTITIES TABLE
-- ===================
CREATE TABLE IF NOT EXISTS entities (
    id              SERIAL PRIMARY KEY,
    entity_type     VARCHAR(100) NOT NULL,      -- 'PERSON' | 'ORG' | 'PRODUCT' | 'GPE' | etc.
    entity_text     VARCHAR(500) NOT NULL,      -- Normalized text (lowercase)
    display_text    VARCHAR(500) NOT NULL,      -- Original text as found
    created_at      TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_entity_type_text UNIQUE(entity_type, entity_text)
);

-- ===================
-- POST_ENTITIES TABLE (Junction table for M:N relationship)
-- ===================
CREATE TABLE IF NOT EXISTS post_entities (
    id          SERIAL PRIMARY KEY,
    post_id     INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    entity_id   INTEGER REFERENCES entities(id) ON DELETE CASCADE,
    confidence  FLOAT,                          -- NER confidence score
    start_pos   INTEGER,                        -- Position in post content
    end_pos     INTEGER,
    created_at  TIMESTAMP DEFAULT NOW(),

    CONSTRAINT uq_post_entity_pos UNIQUE(post_id, entity_id, start_pos)
);

-- ===================
-- INDEXES
-- ===================
CREATE INDEX IF NOT EXISTS idx_posts_listener ON posts(listener_id);
CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
CREATE INDEX IF NOT EXISTS idx_posts_collected_at ON posts(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_sentiment ON posts(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author_handle);
CREATE INDEX IF NOT EXISTS idx_posts_nlp_error ON posts(nlp_error) WHERE nlp_error IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_text ON entities(entity_text);

CREATE INDEX IF NOT EXISTS idx_post_entities_post ON post_entities(post_id);
CREATE INDEX IF NOT EXISTS idx_post_entities_entity ON post_entities(entity_id);

-- ===================
-- DONE
-- ===================
-- Schema initialization complete
