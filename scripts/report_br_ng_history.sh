#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

psql "$DATABASE_URL" -c "
WITH base AS (
    SELECT
        CASE
            WHEN root_symbol IS NOT NULL AND root_symbol <> '' THEN root_symbol
            WHEN symbol LIKE 'BR%' THEN 'BR'
            WHEN symbol LIKE 'NG%' THEN 'NG'
            ELSE root_symbol
        END AS root,
        symbol,
        net_pnl,
        COALESCE(exit_ts, closed_at, created_at) AS ts
    FROM closed_trades
    WHERE symbol LIKE 'BR%'
       OR symbol LIKE 'NG%'
       OR root_symbol IN ('BR','NG')
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
    ROUND(SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)::numeric,6) AS gross_profit,
    ROUND(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END))::numeric,6) AS gross_loss,
    MAX(ts) AS last_trade_ts
FROM base
GROUP BY root, symbol
ORDER BY root, net_pnl DESC;
"
