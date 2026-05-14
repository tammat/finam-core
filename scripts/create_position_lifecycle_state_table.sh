#!/usr/bin/env bash
set -euo pipefail

source /opt/finam-core/deploy/env/.env

psql "$DATABASE_URL" <<'SQL'

CREATE TABLE IF NOT EXISTS position_lifecycle_state (
    id BIGSERIAL PRIMARY KEY,

    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL DEFAULT 'default',

    entry_price NUMERIC,
    initial_qty NUMERIC,
    remaining_qty NUMERIC,

    tp1_done BOOLEAN DEFAULT FALSE,
    tp2_done BOOLEAN DEFAULT FALSE,

    profit_lock_done BOOLEAN DEFAULT FALSE,
    trailing_active BOOLEAN DEFAULT FALSE,

    current_stop NUMERIC,
    current_take_profit NUMERIC,

    raw JSONB DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(symbol, strategy)
);

CREATE INDEX IF NOT EXISTS idx_position_lifecycle_symbol
ON position_lifecycle_state(symbol);

SQL

echo "OK: position_lifecycle_state table created"
