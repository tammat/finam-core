#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import timezone, timedelta

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SYMBOL = os.getenv("GOLD_SYMBOL", "GDM6@RTSX")
TIMEFRAME = os.getenv("GOLD_TIMEFRAME", "M5")
EXIT_BARS = int(os.getenv("GOLD_EXIT_BARS", "10"))

MSK = timezone(timedelta(hours=3))

SQL = """
SELECT ts, close
FROM market_bars
WHERE symbol=%s
  AND timeframe=%s
ORDER BY ts
"""

def metrics(values):
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x <= 0]

    gp = sum(wins)
    gl = abs(sum(losses))
    net = sum(values)

    pf = None
    if gl > 0:
        pf = round(gp / gl, 4)

    trades = len(values)

    return {
        "trades": trades,
        "net": round(net, 6),
        "expectancy": round(net / trades, 6) if trades else 0,
        "winrate": round(100 * len(wins) / trades, 2) if trades else 0,
        "pf": pf,
    }

def session(hour):
    if 7 <= hour < 10:
        return "утро"
    if 10 <= hour < 14:
        return "середина"
    if 14 <= hour < 19:
        return "вечер"
    return "прочее"

with psycopg2.connect(DATABASE_URL) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

        cur.execute(SQL, (SYMBOL, TIMEFRAME))
        rows = list(cur.fetchall())

closes = [float(r["close"]) for r in rows]
timestamps = [r["ts"] for r in rows]

all_pnl = []
evening_pnl = []
hour16_pnl = []
hour15_18_pnl = []

for i in range(20, len(closes) - EXIT_BARS):

    mean20 = sum(closes[i-20:i]) / 20.0

    entry = closes[i]
    exit_price = closes[i + EXIT_BARS]

    if entry < mean20 * 0.998:

        pnl = entry - exit_price

        hour = timestamps[i].astimezone(MSK).hour

        all_pnl.append(pnl)

        if session(hour) == "вечер":
            evening_pnl.append(pnl)

        if hour == 16:
            hour16_pnl.append(pnl)

        if 15 <= hour <= 18:
            hour15_18_pnl.append(pnl)

variants = {
    "ALL_SHORT": all_pnl,
    "EVENING_ONLY": evening_pnl,
    "HOUR_16_ONLY": hour16_pnl,
    "HOUR_15_18": hour15_18_pnl,
}

print("=== GOLD SHORT ONLY HOUR FILTER EFFECTIVENESS V1 ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

best_name = None
best_expectancy = -999999

for name, pnl in variants.items():

    m = metrics(pnl)

    print(
        f"VARIANT_ROW "
        f"variant={name} "
        f"trades={m['trades']} "
        f"net_pnl={m['net']} "
        f"expectancy={m['expectancy']} "
        f"winrate={m['winrate']} "
        f"profit_factor={m['pf']}"
    )

    if m["expectancy"] > best_expectancy:
        best_expectancy = m["expectancy"]
        best_name = name

print()
print(
    f"BEST_VARIANT "
    f"name={best_name} "
    f"expectancy={best_expectancy}"
)

print("VERDICT=GOLD_HOUR_FILTER_EFFECTIVENESS_RECORDED")
print("GOLD_SHORT_ONLY_HOUR_FILTER_EFFECTIVENESS_V1_OK")
