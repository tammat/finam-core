#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

ACTIVE_SYMBOLS = [
    s.strip()
    for s in os.getenv(
        "ACTIVE_CONTRACT_SCORECARD_SYMBOLS",
        "BRN6@RTSX,NGN6@RTSX,USDRUBF@RTSX",
    ).split(",")
    if s.strip()
]

SQL = """
WITH base AS (
    SELECT
        CASE
            WHEN root_symbol IS NOT NULL AND root_symbol <> '' THEN root_symbol
            WHEN symbol ~ '^BR[A-Z][0-9]@RTSX$' THEN 'BR'
            WHEN symbol ~ '^NG[A-Z][0-9]@RTSX$' THEN 'NG'
            WHEN symbol LIKE 'USDRUB%%' THEN 'USDRUB'
            ELSE split_part(symbol, '@', 1)
        END AS root,
        symbol,
        net_pnl,
        COALESCE(exit_ts, closed_at, created_at) AS trade_ts
    FROM closed_trades
    WHERE symbol = ANY(%s)
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
    MAX(trade_ts) AS last_trade_ts
FROM base
GROUP BY root, symbol
ORDER BY net_pnl DESC;
"""

def profit_factor(gp, gl):
    gp_f = float(gp or 0)
    gl_f = float(gl or 0)
    if gl_f <= 0:
        return None
    return round(gp_f / gl_f, 4)

def status(trades: int, expectancy: float, pf):
    if trades < 20:
        return "NO_DATA"
    if expectancy > 0 and pf is not None and pf > 1.20:
        return "PROMOTE"
    if expectancy < 0:
        return "DISABLE"
    return "WATCH"

def main() -> None:
    print("=== ACTIVE CONTRACT SCORECARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbols={','.join(ACTIVE_SYMBOLS)}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (ACTIVE_SYMBOLS,))
            rows = cur.fetchall()

    print("ACTIVE_CONTRACT_ROWS")
    if not rows:
        print("NONE")

    for r in rows:
        trades = int(r["trades"])
        expectancy = float(r["expectancy"] or 0)
        pf = profit_factor(r["gross_profit"], r["gross_loss"])
        st = status(trades, expectancy, pf)

        print(
            "ACTIVE_ROW "
            f"root={r['root']} "
            f"symbol={r['symbol']} "
            f"trades={trades} "
            f"net_pnl={r['net_pnl']} "
            f"expectancy={r['expectancy']} "
            f"winrate={r['winrate']} "
            f"profit_factor={pf} "
            f"status={st} "
            f"last_trade_ts={r['last_trade_ts']}"
        )

    print()
    print(f"ROWS={len(rows)}")
    print("VERDICT=ACTIVE_CONTRACT_SCORECARD_RECORDED")
    print("ACTIVE_CONTRACT_SCORECARD_V1_OK")

if __name__ == "__main__":
    main()
