#!/usr/bin/env bash
set -euo pipefail

sudo -u postgres psql -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS strategy_performance_history (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL,
    status TEXT NOT NULL,

    trades INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,

    net_pnl DOUBLE PRECISION,
    expectancy DOUBLE PRECISION,
    profit_factor DOUBLE PRECISION,
    winrate DOUBLE PRECISION,

    last_trade_ts TIMESTAMPTZ,

    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_history_created_at
ON strategy_performance_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_history_symbol_created_at
ON strategy_performance_history(symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_history_status
ON strategy_performance_history(status);
SQL

echo "OK: strategy_performance_history created"
