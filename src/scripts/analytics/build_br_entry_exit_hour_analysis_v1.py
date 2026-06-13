#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict
from datetime import timezone, timedelta

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

MSK = timezone(timedelta(hours=3))

SQL = """
SELECT
    symbol,
    net_pnl,
    entry_ts,
    COALESCE(exit_ts, closed_at, created_at) AS exit_ts
FROM closed_trades
WHERE symbol IN ('BRM6@RTSX','BRN6@RTSX')
  AND entry_ts IS NOT NULL
ORDER BY entry_ts;
"""

def calc(values):
    trades = len(values)
    wins = len([x for x in values if x > 0])
    losses = trades - wins

    gp = sum(x for x in values if x > 0)
    gl = abs(sum(x for x in values if x <= 0))

    net = sum(values)

    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "net": round(net, 6),
        "expectancy": round(net / trades, 6) if trades else 0,
        "pf": round(gp / gl, 4) if gl else None,
        "winrate": round(wins * 100.0 / trades, 2) if trades else 0,
    }

print("=== BR ENTRY EXIT HOUR ANALYSIS V1 ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

with psycopg2.connect(DATABASE_URL) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(SQL)
        rows = cur.fetchall()

entry_groups = defaultdict(list)
exit_groups = defaultdict(list)
entry_exit_groups = defaultdict(list)

for r in rows:
    pnl = float(r["net_pnl"] or 0)

    entry_hour = r["entry_ts"].astimezone(MSK).hour
    exit_hour = r["exit_ts"].astimezone(MSK).hour

    symbol = r["symbol"]

    entry_groups[(symbol, entry_hour)].append(pnl)
    exit_groups[(symbol, exit_hour)].append(pnl)
    entry_exit_groups[(symbol, entry_hour, exit_hour)].append(pnl)

print("ENTRY_HOUR_ROWS")

for key in sorted(entry_groups):
    symbol, hour = key
    m = calc(entry_groups[key])

    print(
        f"ENTRY_HOUR_ROW "
        f"symbol={symbol} "
        f"hour_msk={hour} "
        f"trades={m['trades']} "
        f"net_pnl={m['net']} "
        f"expectancy={m['expectancy']} "
        f"pf={m['pf']} "
        f"winrate={m['winrate']}"
    )

print()
print("EXIT_HOUR_ROWS")

for key in sorted(exit_groups):
    symbol, hour = key
    m = calc(exit_groups[key])

    print(
        f"EXIT_HOUR_ROW "
        f"symbol={symbol} "
        f"hour_msk={hour} "
        f"trades={m['trades']} "
        f"net_pnl={m['net']} "
        f"expectancy={m['expectancy']} "
        f"pf={m['pf']} "
        f"winrate={m['winrate']}"
    )

print()
print("ENTRY_EXIT_ROWS")

for key in sorted(entry_exit_groups):
    symbol, entry_hour, exit_hour = key

    values = entry_exit_groups[key]

    if len(values) < 5:
        continue

    m = calc(values)

    print(
        f"ENTRY_EXIT_ROW "
        f"symbol={symbol} "
        f"entry_hour={entry_hour} "
        f"exit_hour={exit_hour} "
        f"trades={m['trades']} "
        f"net_pnl={m['net']} "
        f"expectancy={m['expectancy']} "
        f"pf={m['pf']}"
    )

print()
print(f"ROWS={len(rows)}")
print("VERDICT=BR_ENTRY_EXIT_HOUR_ANALYSIS_RECORDED")
print("BR_ENTRY_EXIT_HOUR_ANALYSIS_V1_OK")
