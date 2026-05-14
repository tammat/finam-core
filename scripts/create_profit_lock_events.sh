#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS profit_lock_events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol TEXT NOT NULL,
    action TEXT NOT NULL,
    qty DOUBLE PRECISION,
    qty_to_close DOUBLE PRECISION,
    price DOUBLE PRECISION,
    entry_price DOUBLE PRECISION,
    base_stop DOUBLE PRECISION,
    new_stop DOUBLE PRECISION,
    reason TEXT,
    dry_run BOOLEAN NOT NULL DEFAULT true,
    raw JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_profit_lock_events_ts
ON profit_lock_events(ts DESC);

CREATE INDEX IF NOT EXISTS ix_profit_lock_events_symbol_ts
ON profit_lock_events(symbol, ts DESC);
SQL

echo "OK: profit_lock_events table created"
