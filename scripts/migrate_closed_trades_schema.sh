#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS entry_ts TIMESTAMPTZ;

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS exit_ts TIMESTAMPTZ;

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS qty DOUBLE PRECISION;

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS entry_price DOUBLE PRECISION;

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS exit_price DOUBLE PRECISION;

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS gross_pnl DOUBLE PRECISION;

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS commission DOUBLE PRECISION DEFAULT 0;

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS net_pnl DOUBLE PRECISION;

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS trade_source TEXT DEFAULT 'paper';

ALTER TABLE closed_trades
    ADD COLUMN IF NOT EXISTS payload JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_closed_trades_exit_ts
ON closed_trades(exit_ts DESC);

CREATE INDEX IF NOT EXISTS idx_closed_trades_symbol_exit_ts
ON closed_trades(symbol, exit_ts DESC);

SQL

echo "OK: closed_trades schema migrated"
