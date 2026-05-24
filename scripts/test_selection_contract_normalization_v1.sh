#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -c "
SELECT
    strategy,
    symbol,
    root_symbol,
    regime,
    status,
    trades,
    expectancy,
    profit_factor
FROM strategy_selection_state
ORDER BY strategy, root_symbol, symbol, regime;
"

psql "$DATABASE_URL" -c "
SELECT
    strategy,
    root_symbol,
    regime,
    status,
    trades,
    avg_expectancy,
    avg_profit_factor,
    worst_drawdown
FROM strategy_selection_runtime_normalized
ORDER BY strategy, root_symbol, regime;
"

echo "SELECTION_CONTRACT_NORMALIZATION_V1_TEST_OK"
