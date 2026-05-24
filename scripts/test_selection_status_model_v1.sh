#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" <<'SQL'
SELECT status
FROM strategy_selection_state
WHERE status NOT IN (
    'WATCH',
    'ENABLED_RESEARCH',
    'PROMOTED_RUNTIME',
    'DISABLED'
);
SQL

psql "$DATABASE_URL" -c "
SELECT
    strategy,
    symbol,
    regime,
    status,
    trades,
    expectancy,
    profit_factor,
    max_drawdown
FROM strategy_selection_state
ORDER BY strategy, symbol, regime;
"

echo "SELECTION_STATUS_MODEL_V1_TEST_OK"
