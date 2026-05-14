#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS trailing_order_events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    side TEXT,
    qty DOUBLE PRECISION,
    stop_price DOUBLE PRECISION,
    reason TEXT,
    dry_run BOOLEAN NOT NULL DEFAULT true,
    raw JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_trailing_order_events_ts
ON trailing_order_events(ts DESC);

CREATE INDEX IF NOT EXISTS ix_trailing_order_events_symbol_ts
ON trailing_order_events(symbol, ts DESC);
SQL

echo "OK: trailing_order_events table created"
