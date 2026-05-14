#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS manual_broker_position_snapshots (
    id BIGSERIAL PRIMARY KEY,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,

    average_price DOUBLE PRECISION,
    current_price DOUBLE PRECISION,
    unrealized_pnl DOUBLE PRECISION,

    source TEXT NOT NULL DEFAULT 'finam_api',

    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_manual_broker_position_snapshots_symbol_created_at
ON manual_broker_position_snapshots(symbol, created_at DESC);
SQL

echo "OK: manual_broker_position_snapshots created"
