#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" <<'SQL'
CREATE TABLE IF NOT EXISTS closed_trades (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL DEFAULT 'unknown',
    timeframe TEXT NOT NULL DEFAULT 'unknown',
    side TEXT NOT NULL,
    qty NUMERIC NOT NULL,
    entry_price NUMERIC NOT NULL,
    exit_price NUMERIC NOT NULL,
    gross_pnl NUMERIC NOT NULL,
    commission NUMERIC NOT NULL DEFAULT 0,
    net_pnl NUMERIC NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL,
    closed_at TIMESTAMPTZ NOT NULL,
    holding_seconds INTEGER NOT NULL,
    source TEXT NOT NULL DEFAULT 'closed_trade_engine_v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_closed_trades_symbol_strategy
ON closed_trades(symbol, strategy);

CREATE INDEX IF NOT EXISTS idx_closed_trades_closed_at
ON closed_trades(closed_at DESC);
SQL

echo "CLOSED_TRADES_V1_MIGRATION_OK"
