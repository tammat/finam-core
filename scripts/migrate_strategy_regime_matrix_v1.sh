#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS strategy_regime_matrix (
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
    net_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(20,8) NOT NULL DEFAULT 0,
    expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,
    winrate NUMERIC(20,8) NOT NULL DEFAULT 0,

    context_status TEXT NOT NULL,
    runtime_action TEXT NOT NULL,
    score_adjustment NUMERIC(20,8) NOT NULL DEFAULT 0,
    confidence_adjustment NUMERIC(20,8) NOT NULL DEFAULT 0,

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

CREATE INDEX IF NOT EXISTS idx_strategy_regime_matrix_runtime_action
ON strategy_regime_matrix(runtime_action);

CREATE INDEX IF NOT EXISTS idx_strategy_regime_matrix_lookup
ON strategy_regime_matrix(strategy, timeframe, regime, trend, volatility);

CREATE INDEX IF NOT EXISTS idx_strategy_regime_matrix_symbol
ON strategy_regime_matrix(symbol, strategy, timeframe);
SQL

echo "STRATEGY_REGIME_MATRIX_V1_MIGRATION_OK"
