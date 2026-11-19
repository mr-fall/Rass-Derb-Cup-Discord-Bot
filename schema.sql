-- Schema for Rass Derb Cup Discord Bot (PostgreSQL)

CREATE TABLE IF NOT EXISTS discord_form_sections (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    slug VARCHAR(50) NOT NULL,
    title VARCHAR(100) NOT NULL,
    staff_channel_id BIGINT,
    embed_color INTEGER NOT NULL DEFAULT 3049182, -- 0x2E86DE
    image_url TEXT,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS discord_form_sections_guild_slug_unique 
    ON discord_form_sections (guild_id, slug);

CREATE INDEX IF NOT EXISTS discord_form_sections_guild_active_idx 
    ON discord_form_sections (guild_id, active);

CREATE TABLE IF NOT EXISTS discord_form_questions (
    id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES discord_form_sections(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    prompt VARCHAR(45) NOT NULL,
    input_style VARCHAR(12) NOT NULL DEFAULT 'short',
    placeholder VARCHAR(100),
    required BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS discord_form_questions_section_position_idx 
    ON discord_form_questions (section_id, position);

CREATE TABLE IF NOT EXISTS discord_form_buttons (
    id VARCHAR(36) PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    section_id INTEGER NOT NULL REFERENCES discord_form_sections(id) ON DELETE CASCADE,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    label VARCHAR(80) NOT NULL,
    style VARCHAR(12) NOT NULL DEFAULT 'primary',
    custom_id VARCHAR(100) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS discord_form_buttons_message_unique 
    ON discord_form_buttons (message_id);

CREATE INDEX IF NOT EXISTS discord_form_buttons_guild_active_idx 
    ON discord_form_buttons (guild_id, active);
