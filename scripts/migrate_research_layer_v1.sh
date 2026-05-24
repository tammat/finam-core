#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" <<'SQL'
CREATE TABLE IF NOT EXISTS strategy_research_results (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    regime TEXT NOT NULL DEFAULT 'unknown',

    trades INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,

    total_pnl NUMERIC NOT NULL DEFAULT 0,
    avg_pnl NUMERIC NOT NULL DEFAULT 0,
    win_rate NUMERIC NOT NULL DEFAULT 0,
    profit_factor NUMERIC NOT NULL DEFAULT 0,
    expectancy NUMERIC NOT NULL DEFAULT 0,
    max_drawdown NUMERIC NOT NULL DEFAULT 0,

    decision TEXT NOT NULL,
    reason TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_strategy_research_results_run_id
ON strategy_research_results(run_id);

CREATE INDEX IF NOT EXISTS idx_strategy_research_results_strategy_symbol_regime
ON strategy_research_results(strategy, symbol, regime);

CREATE INDEX IF NOT EXISTS idx_strategy_research_results_created_at
ON strategy_research_results(created_at DESC);
SQL

echo "RESEARCH_LAYER_V1_MIGRATION_OK"
