#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" <<'SQL'
CREATE TABLE IF NOT EXISTS strategy_selection_state (
    id BIGSERIAL PRIMARY KEY,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    regime TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'WATCH',
    source_run_id TEXT NOT NULL,
    trades INTEGER NOT NULL,
    expectancy NUMERIC NOT NULL,
    profit_factor NUMERIC NOT NULL,
    max_drawdown NUMERIC NOT NULL,
    reason TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(strategy, symbol, regime)
);

CREATE INDEX IF NOT EXISTS idx_strategy_selection_state_status
ON strategy_selection_state(status);

CREATE INDEX IF NOT EXISTS idx_strategy_selection_state_symbol_regime
ON strategy_selection_state(symbol, regime);
SQL

echo "SELECTION_LAYER_V1_MIGRATION_OK"
