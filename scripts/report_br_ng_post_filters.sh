#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

SINCE_UTC="${SINCE_UTC:-2026-06-08 14:40:00+00}"

echo "=== BR / NG POST-FILTER SCORECARD ==="
echo "since_utc=$SINCE_UTC"
echo

psql "$DATABASE_URL" -c "
WITH base AS (
    SELECT
        CASE
            WHEN root_symbol IS NOT NULL AND root_symbol <> '' THEN root_symbol
            WHEN symbol LIKE 'BR%' THEN 'BR'
            WHEN symbol LIKE 'NG%' THEN 'NG'
            ELSE split_part(symbol,'@',1)
        END AS root,
        symbol,
        net_pnl,
        COALESCE(exit_ts, closed_at, created_at) AS ts
    FROM closed_trades
    WHERE COALESCE(exit_ts, closed_at, created_at) >= '$SINCE_UTC'
      AND (
          symbol LIKE 'BR%'
          OR symbol LIKE 'NG%'
          OR root_symbol IN ('BR','NG')
      )
)
SELECT
    root,
    symbol,
    COUNT(*) AS trades,
    ROUND(SUM(net_pnl)::numeric,6) AS net_pnl,
    ROUND(AVG(net_pnl)::numeric,6) AS expectancy,
    ROUND(
        100.0 * SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0),
        2
    ) AS winrate,
    MAX(ts) AS last_trade_ts
FROM base
GROUP BY root, symbol
ORDER BY root, net_pnl DESC;
"

echo
echo "BR_NG_POST_FILTER_SCORECARD_OK"
