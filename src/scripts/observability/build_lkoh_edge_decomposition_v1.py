#!/usr/bin/env python3

import os
from collections import deque, defaultdict
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")
SYMBOL = "LKOH@MISX"

if not DATABASE_URL:
    raise SystemExit("DATABASE_URL_NOT_SET")

SQL = """
SELECT
    side,
    qty,
    price,
    ts
FROM fills
WHERE symbol = %s
  AND qty > 0
  AND price > 0
  AND price BETWEEN 1000 AND 10000
ORDER BY ts ASC;
"""

def calc_stats(pnls):
    trades = len(pnls)
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net_pnl = sum(pnls)

    winrate = len(wins) / trades * 100 if trades else 0.0
    pf = gross_profit / gross_loss if gross_loss else None
    expectancy = net_pnl / trades if trades else 0.0

    return trades, winrate, net_pnl, pf, expectancy

with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
    fills = list(conn.execute(SQL, (SYMBOL,)))

open_buys = deque()
closed = []

for f in fills:
    side = str(f["side"]).upper()
    qty = float(f["qty"] or 0)
    price = float(f["price"] or 0)
    ts = f["ts"]

    if qty <= 0 or price <= 0:
        continue

    if side == "BUY":
        open_buys.append({"qty": qty, "price": price, "ts": ts})
        continue

    if side == "SELL":
        remaining = qty

        while remaining > 0 and open_buys:
            b = open_buys[0]
            matched = min(remaining, b["qty"])
            pnl = (price - b["price"]) * matched

            closed.append(
                {
                    "entry_ts": b["ts"],
                    "exit_ts": ts,
                    "qty": matched,
                    "entry": b["price"],
                    "exit": price,
                    "pnl": pnl,
                }
            )

            b["qty"] -= matched
            remaining -= matched

            if b["qty"] <= 1e-12:
                open_buys.popleft()

by_hour = defaultdict(list)
by_weekday = defaultdict(list)

for trade in closed:
    # В базе UTC, для МСК +3 часа.
    hour_msk = (int(trade["entry_ts"].strftime("%H")) + 3) % 24
    weekday = trade["entry_ts"].strftime("%A")

    by_hour[hour_msk].append(trade["pnl"])
    by_weekday[weekday].append(trade["pnl"])

print("=== LKOH EDGE DECOMPOSITION V1 ===")
print()
print(f"symbol={SYMBOL}")
print(f"closed_trades={len(closed)}")
print()

print("=== ПО ЧАСАМ МСК ===")
print("hour  trades  winrate   net_pnl      pf        expectancy  status")

for hour in sorted(by_hour):
    trades, winrate, net_pnl, pf, expectancy = calc_stats(by_hour[hour])

    if trades < 20:
        status = "МАЛО_ДАННЫХ"
    elif pf is not None and pf > 1.15 and expectancy > 0:
        status = "СИЛЬНЫЙ"
    elif pf is not None and pf > 1.0 and expectancy > 0:
        status = "РАБОЧИЙ"
    else:
        status = "ИСКЛЮЧИТЬ"

    pf_text = "INF" if pf is None else f"{pf:.4f}"

    print(
        f"{hour:>4}  "
        f"{trades:>6}  "
        f"{winrate:>6.2f}%  "
        f"{net_pnl:>9.4f}  "
        f"{pf_text:>8}  "
        f"{expectancy:>10.4f}  "
        f"{status}"
    )

print()
print("=== ПО ДНЯМ НЕДЕЛИ ===")
print("weekday     trades  winrate   net_pnl      pf        expectancy  status")

weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

for weekday in weekday_order:
    if weekday not in by_weekday:
        continue

    trades, winrate, net_pnl, pf, expectancy = calc_stats(by_weekday[weekday])

    if trades < 20:
        status = "МАЛО_ДАННЫХ"
    elif pf is not None and pf > 1.15 and expectancy > 0:
        status = "СИЛЬНЫЙ"
    elif pf is not None and pf > 1.0 and expectancy > 0:
        status = "РАБОЧИЙ"
    else:
        status = "ИСКЛЮЧИТЬ"

    pf_text = "INF" if pf is None else f"{pf:.4f}"

    print(
        f"{weekday:<10}  "
        f"{trades:>6}  "
        f"{winrate:>6.2f}%  "
        f"{net_pnl:>9.4f}  "
        f"{pf_text:>8}  "
        f"{expectancy:>10.4f}  "
        f"{status}"
    )
