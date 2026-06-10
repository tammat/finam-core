#!/usr/bin/env python3
from __future__ import annotations

import os
import math
import psycopg2
import psycopg2.extras

SQL = """
SELECT
    COALESCE(entry_ts, opened_at, closed_at) AS ts,
    net_pnl
FROM closed_trades
WHERE symbol='BRM6@RTSX'
  AND side='LONG'
  AND trade_source='paper'
  AND source='closed_trade_engine_v1_1'
  AND EXTRACT(HOUR FROM (COALESCE(entry_ts, opened_at) AT TIME ZONE 'Europe/Moscow'))
      BETWEEN 10 AND 13
ORDER BY COALESCE(entry_ts, opened_at, closed_at), id;
"""

def metrics(values: list[float]) -> dict:
    trades = len(values)
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x <= 0]
    gp = sum(wins)
    gl = abs(sum(losses))
    net = sum(values)

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": round(net, 6),
        "expectancy": round(net / trades, 6) if trades else 0,
        "profit_factor": round(gp / gl, 4) if gl > 0 else None,
        "winrate": round(100.0 * len(wins) / trades, 2) if trades else 0,
    }

def print_row(name: str, values: list[float]) -> dict:
    m = metrics(values)
    print(
        "DECAY_ROW "
        f"bucket={name} "
        f"trades={m['trades']} "
        f"wins={m['wins']} "
        f"losses={m['losses']} "
        f"net_pnl={m['net_pnl']} "
        f"expectancy={m['expectancy']} "
        f"winrate={m['winrate']} "
        f"profit_factor={m['profit_factor']}"
    )
    return m

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== SESSION SIDE EDGE RECENT DECAY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("candidate=BRM6_LONG_московская_середина")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    values = [float(r["net_pnl"] or 0) for r in rows]
    total = len(values)

    if total < 20:
        print(f"TOTAL_TRADES={total}")
        print("VERDICT=EDGE_RECENT_DECAY_NO_DATA")
        print("SESSION_SIDE_EDGE_RECENT_DECAY_V1_OK")
        return

    split = math.floor(total * 0.75)

    early = values[:split]
    recent = values[split:]

    print("DECAY_ROWS")
    all_m = print_row("ALL", values)
    early_m = print_row("EARLY_75", early)
    recent_m = print_row("RECENT_25", recent)

    expectancy_delta = round(recent_m["expectancy"] - early_m["expectancy"], 6)
    pf_delta = None
    if recent_m["profit_factor"] is not None and early_m["profit_factor"] is not None:
        pf_delta = round(recent_m["profit_factor"] - early_m["profit_factor"], 4)

    print()
    print(
        "DECAY_SUMMARY "
        f"total_trades={total} "
        f"early_trades={early_m['trades']} "
        f"recent_trades={recent_m['trades']} "
        f"early_expectancy={early_m['expectancy']} "
        f"recent_expectancy={recent_m['expectancy']} "
        f"expectancy_delta={expectancy_delta} "
        f"early_pf={early_m['profit_factor']} "
        f"recent_pf={recent_m['profit_factor']} "
        f"pf_delta={pf_delta}"
    )

    if recent_m["expectancy"] <= 0 and recent_m["trades"] >= 10:
        verdict = "EDGE_RECENT_DECAY_CONFIRMED"
    elif expectancy_delta < 0:
        verdict = "EDGE_RECENT_DECAY_WARNING"
    else:
        verdict = "EDGE_RECENT_DECAY_NOT_CONFIRMED"

    print(f"VERDICT={verdict}")
    print("SESSION_SIDE_EDGE_RECENT_DECAY_V1_OK")

if __name__ == "__main__":
    main()
