#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

set -a
. /opt/finam-core/.env
set +a

echo "GOVERNANCE_FINANCIAL_RESULT_V1"

echo "=== COMMON GOVERNANCE FINANCIAL RESULT: BR/USD ==="
psql "$DATABASE_URL" -c "
WITH gov AS (
    SELECT
        symbol,
        side,
        'common_runtime_governance' AS governance_layer,
        COUNT(*) AS governance_rows,
        SUM(CASE WHEN allowed THEN 1 ELSE 0 END) AS allowed_rows,
        SUM(CASE WHEN NOT allowed THEN 1 ELSE 0 END) AS blocked_rows,
        AVG(expectancy_points) AS avg_governance_expectancy,
        MAX(created_at) AS last_governance_ts
    FROM runtime_governance_live_accumulation_v1
    WHERE symbol ~ '^(BR|USD|USDRUB)'
    GROUP BY symbol, side
),
ct AS (
    SELECT
        symbol,
        CASE
            WHEN side IN ('LONG', 'BUY') THEN 'BUY'
            WHEN side IN ('SHORT', 'SELL') THEN 'SELL'
            ELSE side
        END AS side,
        COUNT(*) AS closed_trades,
        SUM(gross_pnl) AS gross_pnl_sum,
        SUM(net_pnl) AS net_pnl_sum,
        AVG(net_pnl) AS avg_net_pnl,
        SUM(commission) AS commission_sum,
        MAX(COALESCE(closed_at, exit_ts, created_at)) AS last_closed
    FROM closed_trades
    WHERE symbol ~ '^(BR|USD|USDRUB)'
    GROUP BY symbol,
        CASE
            WHEN side IN ('LONG', 'BUY') THEN 'BUY'
            WHEN side IN ('SHORT', 'SELL') THEN 'SELL'
            ELSE side
        END
)
SELECT
    COALESCE(g.symbol, ct.symbol) AS symbol,
    COALESCE(g.side, ct.side) AS side,
    COALESCE(g.governance_layer, 'no_common_governance') AS governance_layer,
    COALESCE(g.governance_rows, 0) AS governance_rows,
    COALESCE(g.allowed_rows, 0) AS allowed_rows,
    COALESCE(g.blocked_rows, 0) AS blocked_rows,
    ROUND(g.avg_governance_expectancy::numeric, 6) AS avg_governance_expectancy,
    COALESCE(ct.closed_trades, 0) AS closed_trades,
    ROUND(ct.gross_pnl_sum::numeric, 4) AS gross_pnl_sum,
    ROUND(ct.net_pnl_sum::numeric, 4) AS net_pnl_sum,
    ROUND(ct.avg_net_pnl::numeric, 6) AS avg_net_pnl,
    ROUND(ct.commission_sum::numeric, 4) AS commission_sum,
    g.last_governance_ts,
    ct.last_closed,
    CASE
        WHEN COALESCE(g.governance_rows, 0) > 0
         AND COALESCE(g.allowed_rows, 0) = 0
         AND COALESCE(ct.net_pnl_sum, 0) > 0
            THEN 'CONFLICT_BLOCKS_PROFITABLE_HISTORY'
        WHEN COALESCE(g.governance_rows, 0) > 0
         AND COALESCE(ct.net_pnl_sum, 0) < 0
            THEN 'GOVERNANCE_EXISTS_BUT_FINANCIAL_EDGE_NEGATIVE'
        WHEN COALESCE(g.governance_rows, 0) > 0
         AND COALESCE(ct.net_pnl_sum, 0) > 0
            THEN 'GOVERNANCE_AND_FINANCIAL_EDGE_POSITIVE'
        WHEN COALESCE(g.governance_rows, 0) = 0
         AND COALESCE(ct.closed_trades, 0) > 0
            THEN 'FINANCIAL_HISTORY_WITHOUT_COMMON_GOVERNANCE'
        ELSE 'INSUFFICIENT_DATA'
    END AS diagnostic_status
FROM gov g
FULL OUTER JOIN ct
  ON ct.symbol = g.symbol
 AND ct.side = g.side
ORDER BY
    COALESCE(ct.net_pnl_sum, 0) DESC,
    COALESCE(g.governance_rows, 0) DESC;
"

echo "=== NG GOVERNANCE FINANCIAL RESULT ==="
psql "$DATABASE_URL" -c "
WITH ng_gov AS (
    SELECT
        symbol,
        'BUY' AS side,
        'ng_runtime_governance' AS governance_layer,
        COUNT(*) AS governance_rows,
        SUM(CASE WHEN allow_runtime THEN 1 ELSE 0 END) AS allowed_rows,
        SUM(CASE WHEN NOT allow_runtime THEN 1 ELSE 0 END) AS blocked_rows,
        AVG(expectancy) AS avg_governance_expectancy,
        AVG(profit_factor) AS avg_policy_pf,
        MAX(calculated_at) AS last_governance_ts
    FROM ng_m1_runtime_policy
    GROUP BY symbol
),
ct AS (
    SELECT
        symbol,
        CASE
            WHEN side IN ('LONG', 'BUY') THEN 'BUY'
            WHEN side IN ('SHORT', 'SELL') THEN 'SELL'
            ELSE side
        END AS side,
        COUNT(*) AS closed_trades,
        SUM(gross_pnl) AS gross_pnl_sum,
        SUM(net_pnl) AS net_pnl_sum,
        AVG(net_pnl) AS avg_net_pnl,
        SUM(commission) AS commission_sum,
        MAX(COALESCE(closed_at, exit_ts, created_at)) AS last_closed
    FROM closed_trades
    WHERE symbol LIKE 'NG%'
    GROUP BY symbol,
        CASE
            WHEN side IN ('LONG', 'BUY') THEN 'BUY'
            WHEN side IN ('SHORT', 'SELL') THEN 'SELL'
            ELSE side
        END
)
SELECT
    COALESCE(g.symbol, ct.symbol) AS symbol,
    COALESCE(g.side, ct.side) AS side,
    COALESCE(g.governance_layer, 'no_ng_governance') AS governance_layer,
    COALESCE(g.governance_rows, 0) AS governance_rows,
    COALESCE(g.allowed_rows, 0) AS allowed_rows,
    COALESCE(g.blocked_rows, 0) AS blocked_rows,
    ROUND(g.avg_governance_expectancy::numeric, 6) AS avg_governance_expectancy,
    ROUND(g.avg_policy_pf::numeric, 4) AS avg_policy_pf,
    COALESCE(ct.closed_trades, 0) AS closed_trades,
    ROUND(ct.gross_pnl_sum::numeric, 4) AS gross_pnl_sum,
    ROUND(ct.net_pnl_sum::numeric, 4) AS net_pnl_sum,
    ROUND(ct.avg_net_pnl::numeric, 6) AS avg_net_pnl,
    ROUND(ct.commission_sum::numeric, 4) AS commission_sum,
    g.last_governance_ts,
    ct.last_closed,
    CASE
        WHEN COALESCE(g.governance_rows, 0) > 0
         AND COALESCE(ct.net_pnl_sum, 0) > 0
            THEN 'NG_GOVERNANCE_AND_FINANCIAL_EDGE_POSITIVE'
        WHEN COALESCE(g.governance_rows, 0) > 0
         AND COALESCE(ct.net_pnl_sum, 0) < 0
            THEN 'NG_GOVERNANCE_EXISTS_BUT_FINANCIAL_EDGE_NEGATIVE'
        WHEN COALESCE(g.governance_rows, 0) = 0
         AND COALESCE(ct.closed_trades, 0) > 0
            THEN 'NG_FINANCIAL_HISTORY_WITHOUT_POLICY'
        ELSE 'INSUFFICIENT_DATA'
    END AS diagnostic_status
FROM ng_gov g
FULL OUTER JOIN ct
  ON ct.symbol = g.symbol
 AND ct.side = g.side
ORDER BY
    COALESCE(ct.net_pnl_sum, 0) DESC,
    COALESCE(g.governance_rows, 0) DESC;
"

echo "GOVERNANCE_FINANCIAL_RESULT_V1_OK"
