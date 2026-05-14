#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS position_lifecycle_reconcile_events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL DEFAULT 'default',
    action TEXT NOT NULL,
    expected_qty DOUBLE PRECISION,
    actual_qty DOUBLE PRECISION,
    reason TEXT,
    raw JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_position_lifecycle_reconcile_events_ts
ON position_lifecycle_reconcile_events(ts DESC);

CREATE INDEX IF NOT EXISTS ix_position_lifecycle_reconcile_events_symbol_ts
ON position_lifecycle_reconcile_events(symbol, ts DESC);
SQL

echo "OK: position_lifecycle_reconcile_events table created"
