#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS strategy_regime_performance (
    id BIGSERIAL PRIMARY KEY,

    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    trade_source TEXT NOT NULL,

    regime TEXT NOT NULL,
    trend TEXT NOT NULL,
    volatility TEXT NOT NULL,
    exit_policy TEXT NOT NULL,

    trades INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,

    winrate NUMERIC(20,8) NOT NULL DEFAULT 0,
    net_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_win NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_loss NUMERIC(20,8) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(20,8) NOT NULL DEFAULT 0,
    expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,

    context_quality TEXT NOT NULL DEFAULT 'UNKNOWN',
    status TEXT NOT NULL DEFAULT 'UNKNOWN',
    reason TEXT NOT NULL DEFAULT '',

    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (
        symbol,
        strategy,
        timeframe,
        trade_source,
        regime,
        trend,
        volatility,
        exit_policy
    )
);

CREATE INDEX IF NOT EXISTS idx_strategy_regime_performance_symbol
ON strategy_regime_performance(symbol, strategy, timeframe);

CREATE INDEX IF NOT EXISTS idx_strategy_regime_performance_status
ON strategy_regime_performance(status);

CREATE INDEX IF NOT EXISTS idx_strategy_regime_performance_context
ON strategy_regime_performance(regime, trend, volatility, exit_policy);
SQL

echo "STRATEGY_REGIME_PERFORMANCE_V1_MIGRATION_OK"
