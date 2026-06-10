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

def status(m: dict) -> str:
    pf = m["profit_factor"]
    if m["trades"] < 10:
        return "NO_DATA"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.2:
        return "FAVORABLE"
    if m["expectancy"] > 0:
        return "WATCH"
    return "UNFAVORABLE"

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== SESSION SIDE EDGE WALKFORWARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("candidate=BRM6_LONG_московская_середина")
    print("buckets=4")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    values = [float(r["net_pnl"] or 0) for r in rows]
    total = len(values)

    print("WALKFORWARD_ROWS")

    favorable = 0
    unfavorable = 0
    watch = 0
    no_data = 0

    if total == 0:
        print("WALKFORWARD_ROW bucket=0 trades=0 status=NO_DATA")
        print("VERDICT=EDGE_WALKFORWARD_NO_DATA")
        print("SESSION_SIDE_EDGE_WALKFORWARD_V1_OK")
        return

    bucket_count = 4
    bucket_size = math.ceil(total / bucket_count)

    for idx in range(bucket_count):
        start = idx * bucket_size
        end = min(start + bucket_size, total)
        bucket_values = values[start:end]

        if not bucket_values:
            continue

        m = metrics(bucket_values)
        st = status(m)

        if st == "FAVORABLE":
            favorable += 1
        elif st == "UNFAVORABLE":
            unfavorable += 1
        elif st == "WATCH":
            watch += 1
        else:
            no_data += 1

        print(
            "WALKFORWARD_ROW "
            f"bucket={idx + 1} "
            f"from_trade={start + 1} "
            f"to_trade={end} "
            f"trades={m['trades']} "
            f"wins={m['wins']} "
            f"losses={m['losses']} "
            f"net_pnl={m['net_pnl']} "
            f"expectancy={m['expectancy']} "
            f"winrate={m['winrate']} "
            f"profit_factor={m['profit_factor']} "
            f"status={st}"
        )

    print()
    print(
        "WALKFORWARD_SUMMARY "
        f"total_trades={total} "
        f"favorable={favorable} "
        f"watch={watch} "
        f"unfavorable={unfavorable} "
        f"no_data={no_data}"
    )

    if favorable >= 3 and unfavorable == 0:
        verdict = "EDGE_WALKFORWARD_STABLE"
    elif favorable >= 2 and unfavorable <= 1:
        verdict = "EDGE_WALKFORWARD_MIXED"
    else:
        verdict = "EDGE_WALKFORWARD_UNSTABLE"

    print(f"VERDICT={verdict}")
    print("SESSION_SIDE_EDGE_WALKFORWARD_V1_OK")

if __name__ == "__main__":
    main()
