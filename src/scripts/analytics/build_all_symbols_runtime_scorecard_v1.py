#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SQL = """
SELECT
    root_symbol,
    symbol,
    COUNT(*) AS trades,
    ROUND(SUM(net_pnl)::numeric,6) AS net_pnl,
    ROUND(AVG(net_pnl)::numeric,6) AS expectancy,
    ROUND(
        100.0 *
        SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0),
        2
    ) AS winrate,
    ROUND(
        SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)::numeric,
        6
    ) AS gross_profit,
    ROUND(
        ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END))::numeric,
        6
    ) AS gross_loss,
    MAX(COALESCE(exit_ts, closed_at)) AS last_trade_ts
FROM closed_trades
GROUP BY root_symbol, symbol
ORDER BY net_pnl DESC;
"""

print("=== ALL SYMBOLS RUNTIME SCORECARD V1 ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

with psycopg2.connect(DATABASE_URL) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(SQL)
        rows = cur.fetchall()

print("SYMBOL_SCORECARD")

for r in rows:

    trades = int(r["trades"])
    expectancy = float(r["expectancy"] or 0)

    gp = float(r["gross_profit"] or 0)
    gl = float(r["gross_loss"] or 0)

    if gl > 0:
        pf = round(gp / gl, 4)
    else:
        pf = None

    if trades < 20:
        status = "NO_DATA"
    elif expectancy > 0 and (pf is not None and pf > 1.20):
        status = "PROMOTE"
    elif expectancy < 0:
        status = "DISABLE"
    else:
        status = "WATCH"

    print(
        "SYMBOL_ROW "
        f"root={r['root_symbol']} "
        f"symbol={r['symbol']} "
        f"trades={trades} "
        f"net_pnl={r['net_pnl']} "
        f"expectancy={r['expectancy']} "
        f"winrate={r['winrate']} "
        f"profit_factor={pf} "
        f"status={status} "
        f"last_trade_ts={r['last_trade_ts']}"
    )

print()
print(f"ROWS={len(rows)}")
print("VERDICT=ALL_SYMBOLS_RUNTIME_SCORECARD_RECORDED")
print("ALL_SYMBOLS_RUNTIME_SCORECARD_V1_OK")
