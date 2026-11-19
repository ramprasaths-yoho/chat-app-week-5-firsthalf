-- Schema (also created automatically at startup by SQLAlchemy create_all)
CREATE TABLE IF NOT EXISTS sessions (
    id                UUID PRIMARY KEY,
    api_key_hash      VARCHAR(64) NOT NULL,
    title             VARCHAR(200),
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd          DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_sessions_api_key_hash ON sessions (api_key_hash);

CREATE TABLE IF NOT EXISTS messages (
    id          SERIAL PRIMARY KEY,
    session_id  UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        VARCHAR(16) NOT NULL CHECK (role IN ('system','user','assistant')),
    content     TEXT NOT NULL,
    tokens      INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_messages_session_id ON messages (session_id);

-- Rate limiting + per-key usage. No FK to sessions, so deleting a session
-- does NOT reset a key's hourly quota or erase its usage history.
CREATE TABLE IF NOT EXISTS api_usage (
    id                SERIAL PRIMARY KEY,
    api_key_hash      VARCHAR(64) NOT NULL,
    session_id        UUID,
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    cost_usd          DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_api_usage_key_time ON api_usage (api_key_hash, created_at);
