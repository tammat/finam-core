#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS strategy_research_verdicts (
    id BIGSERIAL PRIMARY KEY,

    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    regime TEXT NOT NULL DEFAULT 'unknown',
    trade_source TEXT NOT NULL DEFAULT 'paper',

    performance_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    walkforward_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    regime_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    performance_pf NUMERIC(20,8) NOT NULL DEFAULT 0,
    walkforward_test_pf NUMERIC(20,8) NOT NULL DEFAULT 0,
    regime_pf NUMERIC(20,8) NOT NULL DEFAULT 0,

    performance_expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,
    walkforward_test_expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,
    regime_expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,

    trades INTEGER NOT NULL DEFAULT 0,
    oos_trades INTEGER NOT NULL DEFAULT 0,

    verdict TEXT NOT NULL,
    confidence NUMERIC(20,8) NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',

    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(strategy, symbol, timeframe, regime, trade_source)
);

CREATE INDEX IF NOT EXISTS idx_strategy_research_verdicts_symbol
ON strategy_research_verdicts(symbol, strategy, timeframe);

CREATE INDEX IF NOT EXISTS idx_strategy_research_verdicts_verdict
ON strategy_research_verdicts(verdict);

CREATE INDEX IF NOT EXISTS idx_strategy_research_verdicts_regime
ON strategy_research_verdicts(regime, timeframe);

CREATE INDEX IF NOT EXISTS idx_strategy_research_verdicts_computed_at
ON strategy_research_verdicts(computed_at DESC);
SQL

echo "STRATEGY_RESEARCH_VERDICTS_V1_MIGRATION_OK"
