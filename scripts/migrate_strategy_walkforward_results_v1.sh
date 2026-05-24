#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS strategy_walkforward_results (
    id BIGSERIAL PRIMARY KEY,

    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    regime TEXT NOT NULL,
    trade_source TEXT NOT NULL,

    train_from TIMESTAMPTZ NOT NULL,
    train_to TIMESTAMPTZ NOT NULL,

    test_from TIMESTAMPTZ NOT NULL,
    test_to TIMESTAMPTZ NOT NULL,

    train_trades INTEGER NOT NULL,
    test_trades INTEGER NOT NULL,

    train_pf NUMERIC(20,8) NOT NULL,
    test_pf NUMERIC(20,8) NOT NULL,

    train_expectancy NUMERIC(20,8) NOT NULL,
    test_expectancy NUMERIC(20,8) NOT NULL,

    train_winrate NUMERIC(20,8) NOT NULL,
    test_winrate NUMERIC(20,8) NOT NULL,

    degradation_score NUMERIC(20,8) NOT NULL,
    stability_score NUMERIC(20,8) NOT NULL,

    status TEXT NOT NULL,
    reason TEXT NOT NULL,

    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_strategy_walkforward_symbol
ON strategy_walkforward_results(symbol, strategy, timeframe);

CREATE INDEX IF NOT EXISTS idx_strategy_walkforward_status
ON strategy_walkforward_results(status);

CREATE INDEX IF NOT EXISTS idx_strategy_walkforward_regime
ON strategy_walkforward_results(regime, timeframe);

CREATE INDEX IF NOT EXISTS idx_strategy_walkforward_computed_at
ON strategy_walkforward_results(computed_at DESC);
SQL

echo "STRATEGY_WALKFORWARD_RESULTS_V1_MIGRATION_OK"
