#!/usr/bin/env python3
from __future__ import annotations

import os
import json
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]
BR_SYMBOLS = ["BRM6@RTSX", "BRN6@RTSX"]

SQL_TRADES = """
SELECT
    symbol,
    COALESCE(side, 'UNKNOWN') AS side,
    COUNT(*) AS rows
FROM trades
WHERE symbol = ANY(%s)
GROUP BY symbol, COALESCE(side, 'UNKNOWN')
ORDER BY symbol, side;
"""

SQL_CLOSED = """
SELECT
    symbol,
    COALESCE(side, 'UNKNOWN') AS side,
    COUNT(*) AS rows,
    ROUND(COALESCE(SUM(net_pnl),0)::numeric,6) AS net_pnl
FROM closed_trades
WHERE symbol = ANY(%s)
GROUP BY symbol, COALESCE(side, 'UNKNOWN')
ORDER BY symbol, side;
"""

def raw_keys(value) -> str:
    if value is None:
        return "NONE"
    if isinstance(value, dict):
        return ",".join(sorted(value.keys())) or "EMPTY"
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return ",".join(sorted(parsed.keys())) or "EMPTY"
    except Exception:
        pass
    return "UNPARSEABLE"

def main() -> None:
    print("=== BR CLOSED TRADE SIDE MATERIALIZATION AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("symbols=BRM6@RTSX,BRN6@RTSX")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            print("TRADE_SIDE_ROWS")
            cur.execute(SQL_TRADES, (BR_SYMBOLS,))
            trade_rows = cur.fetchall()
            for r in trade_rows:
                print(
                    "TRADE_SIDE_ROW "
                    f"symbol={r['symbol']} "
                    f"side={r['side']} "
                    f"rows={r['rows']}"
                )

            print()
            print("CLOSED_SIDE_ROWS")
            cur.execute(SQL_CLOSED, (BR_SYMBOLS,))
            closed_rows = cur.fetchall()
            for r in closed_rows:
                print(
                    "CLOSED_SIDE_ROW "
                    f"symbol={r['symbol']} "
                    f"side={r['side']} "
                    f"rows={r['rows']} "
                    f"net_pnl={r['net_pnl']}"
                )


    trade_sides = {(r["symbol"], r["side"]): int(r["rows"]) for r in trade_rows}
    closed_sides = {(r["symbol"], r["side"]): int(r["rows"]) for r in closed_rows}

    print()
    print("MATERIALIZATION_SUMMARY")

    for symbol in BR_SYMBOLS:
        buy_rows = trade_sides.get((symbol, "BUY"), 0)
        sell_rows = trade_sides.get((symbol, "SELL"), 0)
        long_closed = closed_sides.get((symbol, "LONG"), 0)
        short_closed = closed_sides.get((symbol, "SHORT"), 0)
        unknown_closed = closed_sides.get((symbol, "UNKNOWN"), 0)

        print(
            "MATERIALIZATION_ROW "
            f"symbol={symbol} "
            f"trade_buy_rows={buy_rows} "
            f"trade_sell_rows={sell_rows} "
            f"closed_long_rows={long_closed} "
            f"closed_short_rows={short_closed} "
            f"closed_unknown_rows={unknown_closed}"
        )

    br_sell_total = sum(trade_sides.get((s, "SELL"), 0) for s in BR_SYMBOLS)
    br_short_total = sum(closed_sides.get((s, "SHORT"), 0) for s in BR_SYMBOLS)

    if br_sell_total > 0 and br_short_total == 0:
        verdict = "SELL_NOT_MATERIALIZED_AS_SHORT"
    elif br_sell_total > 0 and br_short_total > 0:
        verdict = "SHORT_MATERIALIZATION_PRESENT"
    else:
        verdict = "NO_SELL_SOURCE_ROWS"

    print(f"VERDICT={verdict}")
    print("BR_CLOSED_TRADE_SIDE_MATERIALIZATION_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
