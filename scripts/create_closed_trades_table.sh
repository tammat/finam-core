#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS closed_trades (
    id BIGSERIAL PRIMARY KEY,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL,
    side TEXT NOT NULL,

    entry_ts TIMESTAMPTZ,
    exit_ts TIMESTAMPTZ,

    qty DOUBLE PRECISION NOT NULL,

    entry_price DOUBLE PRECISION NOT NULL,
    exit_price DOUBLE PRECISION NOT NULL,

    gross_pnl DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION NOT NULL DEFAULT 0,
    net_pnl DOUBLE PRECISION NOT NULL,

    trade_source TEXT NOT NULL DEFAULT 'paper',

    payload JSONB NOT NULL DEFAULT '{}'::jsonb,

    UNIQUE(symbol, side, entry_ts, exit_ts, qty, entry_price, exit_price)
);

CREATE INDEX IF NOT EXISTS idx_closed_trades_exit_ts
ON closed_trades(exit_ts DESC);

CREATE INDEX IF NOT EXISTS idx_closed_trades_symbol_exit_ts
ON closed_trades(symbol, exit_ts DESC);
SQL

echo "OK: closed_trades table created"
