#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS runtime_strategy_scores (
    id BIGSERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    root_symbol TEXT NOT NULL,
    regime TEXT NOT NULL,
    score NUMERIC(20,8) NOT NULL DEFAULT 0,
    confidence NUMERIC(20,8) NOT NULL DEFAULT 0,
    recommendation TEXT NOT NULL DEFAULT 'WATCH',
    source_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    trades INTEGER NOT NULL DEFAULT 0,
    expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(20,8) NOT NULL DEFAULT 0,
    max_drawdown NUMERIC(20,8) NOT NULL DEFAULT 0,
    reason TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runtime_strategy_scores_key
ON runtime_strategy_scores(strategy, root_symbol, regime, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_runtime_strategy_scores_created_at
ON runtime_strategy_scores(created_at DESC);

CREATE OR REPLACE VIEW runtime_strategy_scores_latest AS
SELECT DISTINCT ON (strategy, root_symbol, regime)
    strategy,
    root_symbol,
    regime,
    score,
    confidence,
    recommendation,
    source_status,
    trades,
    expectancy,
    profit_factor,
    max_drawdown,
    reason,
    created_at
FROM runtime_strategy_scores
ORDER BY strategy, root_symbol, regime, created_at DESC;
SQL

echo "RUNTIME_STRATEGY_SCORES_V1_MIGRATION_OK"
