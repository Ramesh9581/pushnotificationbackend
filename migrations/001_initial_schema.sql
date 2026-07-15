-- ============================================================
-- Migration: 001_initial_schema.sql
-- Run this in your Supabase SQL Editor (or via psql)
-- ============================================================

-- ── device_tokens ──────────────────────────────────────────────────────────────
-- Stores FCM registration tokens for each user/device (web only for now).
CREATE TABLE IF NOT EXISTS device_tokens (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       TEXT        NOT NULL,
    platform      TEXT        NOT NULL DEFAULT 'web',   -- 'web' | 'android' | 'ios'
    token         TEXT        NOT NULL UNIQUE,
    device_name   TEXT,                                  -- optional label e.g. "Chrome on Windows"
    is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookup by user_id
CREATE INDEX IF NOT EXISTS idx_device_tokens_user_id ON device_tokens (user_id);

-- ── notification_logs ──────────────────────────────────────────────────────────
-- Records every notification send attempt with its delivery outcome.
CREATE TABLE IF NOT EXISTS notification_logs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT        NOT NULL,
    title           TEXT        NOT NULL,
    message         TEXT        NOT NULL,
    screen_name     TEXT        NOT NULL,               -- e.g. "OrderDetail", "ChatDetail"
    data            JSONB,                              -- optional payload: {order_id, chat_id, ...}
    token           TEXT        NOT NULL,               -- FCM token the notification was sent to
    status          TEXT        NOT NULL DEFAULT 'pending',  -- 'sent' | 'failed'
    error_message   TEXT,                               -- populated on failure
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for filtering logs
CREATE INDEX IF NOT EXISTS idx_notification_logs_user_id  ON notification_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_notification_logs_status   ON notification_logs (status);
CREATE INDEX IF NOT EXISTS idx_notification_logs_sent_at  ON notification_logs (sent_at DESC);

-- ── Auto-update updated_at on device_tokens ───────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_device_tokens_updated_at ON device_tokens;
CREATE TRIGGER set_device_tokens_updated_at
    BEFORE UPDATE ON device_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
