#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

SINCE_UTC="${SINCE_UTC:-2026-06-08 14:40:00+00}"
ACTIVE_BR_SYMBOLS="${ACTIVE_BR_SYMBOLS:-BRN6@RTSX}"
ACTIVE_NG_SYMBOLS="${ACTIVE_NG_SYMBOLS:-NGN6@RTSX}"
ACTIVE_SYMBOLS="${ACTIVE_BR_SYMBOLS},${ACTIVE_NG_SYMBOLS}"

echo "=== BR / NG POST-FILTER ACTIVE CONTRACT SCORECARD ==="
echo "since_utc=$SINCE_UTC"
echo "active_br_symbols=$ACTIVE_BR_SYMBOLS"
echo "active_ng_symbols=$ACTIVE_NG_SYMBOLS"
echo

psql "$DATABASE_URL" -c "
WITH params AS (
    SELECT
        string_to_array('${ACTIVE_SYMBOLS}', ',') AS symbols,
        '${SINCE_UTC}'::timestamptz AS since_utc
),
base AS (
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
    FROM closed_trades, params
    WHERE symbol = ANY(params.symbols)
      AND COALESCE(exit_ts, closed_at, created_at) >= params.since_utc
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
ORDER BY root, symbol;
"

echo
echo "BR_NG_POST_FILTER_ACTIVE_CONTRACT_SCORECARD_OK"
