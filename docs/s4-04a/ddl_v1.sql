-- S4-04a Core DDL v1 (docs only; DO NOT APPLY)
-- Purpose: minimal schema for safe, extensible persistence
-- Notes:
--  - Requires pgcrypto for gen_random_uuid()
--  - UNIQUE(session_id, engine, version) provides composite btree index
--  - Additional indexes (e.g., created_at DESC combos) will be evaluated later

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS translation_sessions (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at         TIMESTAMPTZ,
  legacy_session_key TEXT,
  metadata           JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_ts_legacy_session_key
  ON translation_sessions(legacy_session_key)
  WHERE legacy_session_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS translations (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  UUID NOT NULL REFERENCES translation_sessions(id) ON DELETE CASCADE,
  engine      TEXT NOT NULL,
  version     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT uq_translations_session_engine_version
    UNIQUE (session_id, engine, version)
);

CREATE INDEX IF NOT EXISTS idx_translations_created_at
  ON translations(created_at);

COMMIT;
