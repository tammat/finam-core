#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" <<'SQL'
ALTER TABLE strategy_selection_state
DROP CONSTRAINT IF EXISTS chk_strategy_selection_state_status;

ALTER TABLE strategy_selection_state
ADD CONSTRAINT chk_strategy_selection_state_status
CHECK (
    status IN (
        'WATCH',
        'ENABLED_RESEARCH',
        'PROMOTED_RUNTIME',
        'DISABLED'
    )
);

CREATE INDEX IF NOT EXISTS idx_strategy_selection_state_runtime
ON strategy_selection_state(strategy, symbol, regime)
WHERE status = 'PROMOTED_RUNTIME';

CREATE OR REPLACE VIEW strategy_selection_runtime_enabled AS
SELECT
    strategy,
    symbol,
    regime,
    status,
    trades,
    expectancy,
    profit_factor,
    max_drawdown,
    source_run_id,
    reason,
    updated_at
FROM strategy_selection_state
WHERE status = 'PROMOTED_RUNTIME';
SQL

echo "SELECTION_STATUS_MODEL_V1_MIGRATION_OK"
