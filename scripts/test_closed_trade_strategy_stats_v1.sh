#!/usr/bin/env bash
set -euo pipefail

psql "$DATABASE_URL" -c "
SELECT
    root_symbol,
    strategy,
    timeframe,
    COUNT(*) AS groups
FROM closed_trade_strategy_stats
GROUP BY root_symbol, strategy, timeframe
ORDER BY root_symbol, strategy, timeframe;
"

echo "CLOSED_TRADE_STRATEGY_STATS_V1_OK"
