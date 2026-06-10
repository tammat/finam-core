#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

print("=== RUNTIME EDGE VALIDATION SCORECARD V2 ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

SQL = """
WITH closed AS (
    SELECT
        CASE
            WHEN symbol LIKE 'BR%' THEN 'BR_RUNTIME'
            WHEN symbol LIKE 'NG%' THEN 'NG_RUNTIME'
            WHEN symbol LIKE 'USDRUB%' THEN 'USD_RUNTIME'
            ELSE symbol
        END AS strategy,
        COUNT(*) AS trades,
        COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
        COUNT(*) FILTER (WHERE net_pnl <= 0) AS losses,
        ROUND(COALESCE(SUM(net_pnl),0)::numeric,6) AS net_pnl,
        ROUND(COALESCE(AVG(net_pnl),0)::numeric,6) AS expectancy,
        ROUND(
            (
                SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
                /
                NULLIF(ABS(SUM(CASE WHEN net_pnl <= 0 THEN net_pnl ELSE 0 END)),0)
            )::numeric,
            4
        ) AS profit_factor,
        MAX(COALESCE(exit_ts, closed_at, created_at)) AS last_trade_ts
    FROM closed_trades
    WHERE trade_source='paper'
      AND source='closed_trade_engine_v1_1'
      AND (
          symbol LIKE 'BR%'
          OR symbol LIKE 'NG%'
          OR symbol LIKE 'USDRUB%'
      )
    GROUP BY 1
),
shadow AS (
    SELECT
        symbol,
        strategy,
        COUNT(*) AS shadow_signals,
        MAX(signal_ts) AS last_shadow_ts
    FROM runtime_shadow_gold_signals
    WHERE strategy='gold_short_only_shadow_v1'
    GROUP BY symbol, strategy
),
gov AS (
    SELECT
        candidate,
        decision,
        runtime_allow,
        shadow_allow,
        watch_allow,
        reason,
        created_at,
        ROW_NUMBER() OVER (
            PARTITION BY candidate
            ORDER BY created_at DESC, id DESC
        ) rn
    FROM runtime_governance_shadow_accumulation_v1
)
SELECT
    'BR_RUNTIME' AS strategy,
    'BRM6@RTSX,BRN6@RTSX' AS symbols,
    COALESCE(c.trades,0) AS runtime_trades,
    COALESCE(c.net_pnl,0) AS runtime_net_pnl,
    COALESCE(c.expectancy,0) AS runtime_expectancy,
    c.profit_factor AS runtime_profit_factor,
    c.last_trade_ts,
    NULL::integer AS shadow_signals,
    NULL::timestamptz AS last_shadow_ts,
    COALESCE(g.decision,'NO_GOVERNANCE') AS governance_decision,
    COALESCE(g.runtime_allow,0) AS runtime_allow,
    COALESCE(g.shadow_allow,0) AS shadow_allow,
    COALESCE(g.watch_allow,0) AS watch_allow,
    COALESCE(g.reason,'none') AS governance_reason
FROM closed c
LEFT JOIN gov g
    ON g.candidate='BRM6_LONG_московская_середина'
   AND g.rn=1
WHERE c.strategy='BR_RUNTIME'

UNION ALL

SELECT
    'NG_RUNTIME' AS strategy,
    'NGN6@RTSX' AS symbols,
    COALESCE(c.trades,0),
    COALESCE(c.net_pnl,0),
    COALESCE(c.expectancy,0),
    c.profit_factor,
    c.last_trade_ts,
    NULL::integer,
    NULL::timestamptz,
    'NO_GOVERNANCE',
    0,
    0,
    0,
    'negative_edge'
FROM closed c
WHERE c.strategy='NG_RUNTIME'

UNION ALL

SELECT
    'USD_RUNTIME' AS strategy,
    'USDRUBF@RTSX' AS symbols,
    COALESCE(c.trades,0),
    COALESCE(c.net_pnl,0),
    COALESCE(c.expectancy,0),
    c.profit_factor,
    c.last_trade_ts,
    NULL::integer,
    NULL::timestamptz,
    'WATCH_SMALL_SAMPLE',
    0,
    0,
    1,
    'small_or_old_sample'
FROM closed c
WHERE c.strategy='USD_RUNTIME'

UNION ALL

SELECT
    'GOLD_SHORT_ONLY' AS strategy,
    'GDU6@RTSX' AS symbols,
    0,
    0,
    0,
    NULL::numeric,
    NULL::timestamptz,
    COALESCE(s.shadow_signals,0),
    s.last_shadow_ts,
    'SHADOW_ACCUMULATING',
    0,
    1,
    1,
    'shadow_only_no_execution'
FROM shadow s
WHERE s.symbol='GDU6@RTSX'

ORDER BY strategy;
"""

def status(row: dict) -> str:
    strategy = row["strategy"]
    gov = row["governance_decision"]
    pf = row["runtime_profit_factor"]
    exp = float(row["runtime_expectancy"] or 0)
    trades = int(row["runtime_trades"] or 0)
    shadow = int(row["shadow_signals"] or 0)

    if strategy == "GOLD_SHORT_ONLY":
        return "ACCUMULATING" if shadow > 0 else "NO_DATA"

    if gov == "WATCH_ONLY":
        return "WATCH_ONLY"

    if trades < 30:
        return "WATCH"

    if exp > 0 and pf is not None and float(pf) >= 1.2:
        return "CANDIDATE"

    return "REJECT"

with psycopg2.connect(DATABASE_URL) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(SQL)
        rows = cur.fetchall()

print("EDGE_ROWS")

for row in rows:
    st = status(row)
    print(
        "EDGE_ROW "
        f"strategy={row['strategy']} "
        f"symbols={row['symbols']} "
        f"runtime_trades={row['runtime_trades']} "
        f"runtime_net_pnl={row['runtime_net_pnl']} "
        f"runtime_expectancy={row['runtime_expectancy']} "
        f"runtime_profit_factor={row['runtime_profit_factor']} "
        f"shadow_signals={row['shadow_signals']} "
        f"governance_decision={row['governance_decision']} "
        f"runtime_allow={row['runtime_allow']} "
        f"shadow_allow={row['shadow_allow']} "
        f"watch_allow={row['watch_allow']} "
        f"reason={row['governance_reason']} "
        f"last_trade_ts={row['last_trade_ts']} "
        f"last_shadow_ts={row['last_shadow_ts']} "
        f"status={st}"
    )

print()
print(f"SUMMARY_ROW rows={len(rows)}")
print("VERDICT=RUNTIME_EDGE_VALIDATION_SCORECARD_V2_RECORDED")
print("RUNTIME_EDGE_VALIDATION_SCORECARD_V2_OK")
