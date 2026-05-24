#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" <<'SQL'
ALTER TABLE strategy_selection_state
ADD COLUMN IF NOT EXISTS root_symbol TEXT;

UPDATE strategy_selection_state
SET root_symbol =
    CASE
        WHEN symbol LIKE 'NG%@RTSX' THEN 'NG'
        WHEN symbol LIKE 'BR%@RTSX' THEN 'BR'
        WHEN symbol LIKE 'USDRUB%@RTSX' THEN 'USDRUB'
        ELSE symbol
    END
WHERE root_symbol IS NULL;

CREATE INDEX IF NOT EXISTS idx_strategy_selection_state_root_regime
ON strategy_selection_state(root_symbol, regime, status);

CREATE OR REPLACE VIEW strategy_selection_runtime_normalized AS
SELECT
    strategy,
    root_symbol,
    regime,
    status,
    SUM(trades) AS trades,
    AVG(expectancy) AS avg_expectancy,
    AVG(profit_factor) AS avg_profit_factor,
    MIN(max_drawdown) AS worst_drawdown,
    MAX(updated_at) AS updated_at
FROM strategy_selection_state
WHERE status = 'PROMOTED_RUNTIME'
GROUP BY strategy, root_symbol, regime, status;
SQL

echo "SELECTION_CONTRACT_NORMALIZATION_V1_OK"
