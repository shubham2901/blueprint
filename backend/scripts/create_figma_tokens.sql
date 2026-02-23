-- Figma OAuth tokens
-- Logged-in users: stored by user_id (FK to auth.users when auth enabled)
-- Anonymous users: stored by session_id (from bp_session cookie)
CREATE TABLE IF NOT EXISTS figma_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NULL,
    session_id TEXT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT figma_tokens_owner_check CHECK (user_id IS NOT NULL OR session_id IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS figma_tokens_user_id_key ON figma_tokens(user_id) WHERE user_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS figma_tokens_session_id_key ON figma_tokens(session_id) WHERE session_id IS NOT NULL;
