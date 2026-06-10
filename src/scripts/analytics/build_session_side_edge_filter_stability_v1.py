#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
WITH base AS (
    SELECT
        date_trunc('month', COALESCE(entry_ts, opened_at, closed_at))::date AS month,
        net_pnl
    FROM closed_trades
    WHERE symbol='BRM6@RTSX'
      AND side='LONG'
      AND trade_source='paper'
      AND source='closed_trade_engine_v1_1'
      AND EXTRACT(HOUR FROM (COALESCE(entry_ts, opened_at) AT TIME ZONE 'Europe/Moscow'))
            BETWEEN 10 AND 13
)
SELECT
    month,
    COUNT(*) trades,
    ROUND(SUM(net_pnl)::numeric,6) net_pnl,
    ROUND(AVG(net_pnl)::numeric,6) expectancy,
    ROUND(
        (
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
            /
            NULLIF(ABS(SUM(CASE WHEN net_pnl <= 0 THEN net_pnl ELSE 0 END)),0)
        )::numeric,
        4
    ) profit_factor
FROM base
GROUP BY month
ORDER BY month;
"""

def main():
    dsn = os.environ["DATABASE_URL"]

    print("=== SESSION SIDE EDGE FILTER STABILITY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("candidate=BRM6_LONG_московская_середина")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    positive = 0
    negative = 0

    print("MONTH_ROWS")

    for r in rows:
        pf = r["profit_factor"]

        if r["trades"] < 10:
            status = "NO_DATA"
        elif r["expectancy"] > 0 and pf and pf >= 1.2:
            status = "FAVORABLE"
            positive += 1
        else:
            status = "UNFAVORABLE"
            negative += 1

        print(
            f"MONTH_ROW "
            f"month={r['month']} "
            f"trades={r['trades']} "
            f"net_pnl={r['net_pnl']} "
            f"expectancy={r['expectancy']} "
            f"profit_factor={pf} "
            f"status={status}"
        )

    print()
    print(
        f"STABILITY_SUMMARY "
        f"months={len(rows)} "
        f"positive_months={positive} "
        f"negative_months={negative}"
    )

    if positive >= negative:
        print("VERDICT=EDGE_STABLE")
    else:
        print("VERDICT=EDGE_UNSTABLE")

    print("SESSION_SIDE_EDGE_FILTER_STABILITY_V1_OK")

if __name__ == "__main__":
    main()
