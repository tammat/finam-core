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
    side,
    net_pnl,
    entry_ts,
    COALESCE(exit_ts, closed_at, created_at) AS exit_ts
FROM closed_trades
WHERE symbol IN ('BRM6@RTSX','BRN6@RTSX')
ORDER BY entry_ts;
"""

def metrics(values):
    trades = len(values)

    wins = [x for x in values if x > 0]
    losses = [x for x in values if x <= 0]

    gp = sum(wins)
    gl = abs(sum(losses))

    net = sum(values)

    return {
        "trades": trades,
        "net": round(net, 6),
        "expectancy": round(net / trades, 6) if trades else 0,
        "pf": round(gp / gl, 4) if gl else None,
        "winrate": round(100 * len(wins) / trades, 2) if trades else 0,
    }

print("=== BRN6 REGIME SHIFT ANALYSIS V1 ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

with psycopg2.connect(DATABASE_URL) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(SQL)
        rows = cur.fetchall()

contracts = defaultdict(list)
sides = defaultdict(list)
entry_hours = defaultdict(list)
weekdays = defaultdict(list)

for r in rows:
    symbol = r["symbol"]
    pnl = float(r["net_pnl"] or 0)

    contracts[symbol].append(pnl)

    side = str(r.get("side") or "UNKNOWN")
    sides[(symbol, side)].append(pnl)

    if r["entry_ts"]:
        dt = r["entry_ts"].astimezone(MSK)

        entry_hours[(symbol, dt.hour)].append(pnl)
        weekdays[(symbol, dt.weekday())].append(pnl)

print("CONTRACT_ROWS")

for symbol in sorted(contracts):
    m = metrics(contracts[symbol])

    print(
        f"CONTRACT_ROW "
        f"symbol={symbol} "
        f"trades={m['trades']} "
        f"net_pnl={m['net']} "
        f"expectancy={m['expectancy']} "
        f"profit_factor={m['pf']} "
        f"winrate={m['winrate']}"
    )

print()
print("SIDE_ROWS")

for key in sorted(sides):
    symbol, side = key

    m = metrics(sides[key])

    print(
        f"SIDE_ROW "
        f"symbol={symbol} "
        f"side={side} "
        f"trades={m['trades']} "
        f"net_pnl={m['net']} "
        f"expectancy={m['expectancy']} "
        f"profit_factor={m['pf']}"
    )

print()
print("ENTRY_HOUR_ROWS")

for key in sorted(entry_hours):
    symbol, hour = key

    values = entry_hours[key]

    if len(values) < 5:
        continue

    m = metrics(values)

    print(
        f"ENTRY_HOUR_ROW "
        f"symbol={symbol} "
        f"hour_msk={hour} "
        f"trades={m['trades']} "
        f"net_pnl={m['net']} "
        f"expectancy={m['expectancy']} "
        f"profit_factor={m['pf']}"
    )

print()
print("WEEKDAY_ROWS")

for key in sorted(weekdays):
    symbol, weekday = key

    values = weekdays[key]

    if len(values) < 5:
        continue

    m = metrics(values)

    print(
        f"WEEKDAY_ROW "
        f"symbol={symbol} "
        f"weekday={weekday} "
        f"trades={m['trades']} "
        f"net_pnl={m['net']} "
        f"expectancy={m['expectancy']} "
        f"profit_factor={m['pf']}"
    )

print()
print("REGIME_SHIFT_SUMMARY")

brm6 = metrics(contracts["BRM6@RTSX"])
brn6 = metrics(contracts["BRN6@RTSX"])

pf_delta = round(
    (brm6["pf"] or 0) - (brn6["pf"] or 0),
    4
)

exp_delta = round(
    brm6["expectancy"] - brn6["expectancy"],
    6
)

print(
    f"REGIME_SHIFT_ROW "
    f"base_contract=BRM6@RTSX "
    f"next_contract=BRN6@RTSX "
    f"pf_delta={pf_delta} "
    f"expectancy_delta={exp_delta}"
)

print()
print("VERDICT=BRN6_REGIME_SHIFT_RECORDED")
print("BRN6_REGIME_SHIFT_ANALYSIS_V1_OK")
