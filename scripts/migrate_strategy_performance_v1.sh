#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS strategy_performance (
    id BIGSERIAL PRIMARY KEY,

    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    regime TEXT NOT NULL DEFAULT 'unknown',
    trade_source TEXT NOT NULL DEFAULT 'paper',

    trades INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,

    gross_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    net_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,

    gross_profit NUMERIC(20,8) NOT NULL DEFAULT 0,
    gross_loss NUMERIC(20,8) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(20,8) NOT NULL DEFAULT 0,

    winrate NUMERIC(20,8) NOT NULL DEFAULT 0,
    expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_rr NUMERIC(20,8) NOT NULL DEFAULT 0,

    max_drawdown NUMERIC(20,8) NOT NULL DEFAULT 0,
    sharpe_like NUMERIC(20,8) NOT NULL DEFAULT 0,

    avg_hold_sec NUMERIC(20,8) NOT NULL DEFAULT 0,

    context_quality TEXT NOT NULL DEFAULT 'UNKNOWN',
    status TEXT NOT NULL DEFAULT 'UNKNOWN',
    reason TEXT NOT NULL DEFAULT '',

    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(strategy, symbol, timeframe, regime, trade_source)
);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_symbol
ON strategy_performance(symbol, strategy, timeframe);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_status
ON strategy_performance(status);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_regime
ON strategy_performance(regime, timeframe);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_computed_at
ON strategy_performance(computed_at DESC);
SQL

echo "STRATEGY_PERFORMANCE_V1_MIGRATION_OK"
