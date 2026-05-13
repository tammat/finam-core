#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
ALTER TABLE signals ADD COLUMN IF NOT EXISTS signal_id TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE signals ADD COLUMN IF NOT EXISTS strategy TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS horizon TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS timeframe TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS regime TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS entry_price DOUBLE PRECISION;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS stop_loss DOUBLE PRECISION;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS take_profit DOUBLE PRECISION;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS rr DOUBLE PRECISION;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS rejection_reason TEXT;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS payload JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE signals ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'NEW';

CREATE UNIQUE INDEX IF NOT EXISTS ux_signals_signal_id
ON signals(signal_id)
WHERE signal_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_signals_symbol_created_at
ON signals(symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_signals_status
ON signals(status);

CREATE INDEX IF NOT EXISTS idx_signals_horizon
ON signals(horizon);
SQL

echo "OK: signals schema migrated"
