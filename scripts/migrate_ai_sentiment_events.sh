#!/usr/bin/env bash
set -euo pipefail

DB_NAME="${POSTGRES_DB:-finam_core}"

if sudo -n true 2>/dev/null; then
  PSQL_CMD=(sudo -u postgres psql -d "$DB_NAME")
else
  PSQL_CMD=(psql -d "$DB_NAME")
fi

"${PSQL_CMD[@]}" <<'SQL'
CREATE TABLE IF NOT EXISTS ai_sentiment_events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    symbol TEXT NULL,
    text TEXT NOT NULL,
    label TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_sentiment_events_ts
    ON ai_sentiment_events (ts DESC);

CREATE INDEX IF NOT EXISTS idx_ai_sentiment_events_source
    ON ai_sentiment_events (source);

CREATE INDEX IF NOT EXISTS idx_ai_sentiment_events_symbol
    ON ai_sentiment_events (symbol);

CREATE INDEX IF NOT EXISTS idx_ai_sentiment_events_label
    ON ai_sentiment_events (label);
SQL

echo "OK: ai_sentiment_events migration applied"
