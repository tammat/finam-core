#!/usr/bin/env python3

import os
from collections import deque, defaultdict
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")
import sys

SYMBOL = sys.argv[1]

if not DATABASE_URL:
    raise SystemExit("DATABASE_URL_NOT_SET")

SQL = """
SELECT
    symbol,
    side,
    qty,
    price,
    ts
FROM fills
WHERE symbol = %s
ORDER BY ts ASC;
"""

def hour_msk(ts):
    return ts.astimezone().hour + 3 if False else int(ts.strftime("%H"))

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

trades = len(closed)
wins = [x for x in closed if x["pnl"] > 0]
losses = [x for x in closed if x["pnl"] < 0]

gross_profit = sum(x["pnl"] for x in wins)
gross_loss = abs(sum(x["pnl"] for x in losses))
net_pnl = sum(x["pnl"] for x in closed)

winrate = (len(wins) / trades * 100) if trades else 0.0
profit_factor = (gross_profit / gross_loss) if gross_loss else None
expectancy = (net_pnl / trades) if trades else 0.0

by_hour = defaultdict(list)
for x in closed:
    # Час UTC в базе; для МСК добавляем 3 часа.
    h = (int(x["entry_ts"].strftime("%H")) + 3) % 24
    by_hour[h].append(x["pnl"])

print("=== USD EDGE V1 ===")
print()
print(f"symbol={SYMBOL}")
print(f"closed_trades={trades}")
print(f"wins={len(wins)}")
print(f"losses={len(losses)}")
print(f"winrate={winrate:.2f}%")
print(f"net_pnl={net_pnl:.4f}")
print(f"gross_profit={gross_profit:.4f}")
print(f"gross_loss={gross_loss:.4f}")

if profit_factor is None:
    print("profit_factor=INF")
else:
    print(f"profit_factor={profit_factor:.4f}")

print(f"expectancy={expectancy:.6f}")
print()

print("=== USD EDGE BY HOUR MSK ===")
print("hour_msk  trades  winrate   net_pnl    expectancy")

for h in sorted(by_hour):
    vals = by_hour[h]
    n = len(vals)
    w = len([v for v in vals if v > 0])
    wr = w / n * 100 if n else 0
    pnl = sum(vals)
    exp = pnl / n if n else 0
    print(f"{h:>8}  {n:>6}  {wr:>6.2f}%  {pnl:>8.4f}  {exp:>10.6f}")

print()
print("=== USD CLOSED TRADES ===")
print("entry_ts              exit_ts               qty     entry      exit       pnl")

for x in closed:
    print(
        f"{x['entry_ts']}  "
        f"{x['exit_ts']}  "
        f"{x['qty']:>4.1f}  "
        f"{x['entry']:>8.4f}  "
        f"{x['exit']:>8.4f}  "
        f"{x['pnl']:>9.4f}"
    )

if closed:
    sorted_pnl = sorted([x["pnl"] for x in closed])
    median_pnl = sorted_pnl[len(sorted_pnl) // 2]
    max_win = max(sorted_pnl)
    max_loss = min(sorted_pnl)

    without_max_win = [x for x in closed if x["pnl"] != max_win]
    net_without_max = sum(x["pnl"] for x in without_max_win)
    expectancy_without_max = net_without_max / len(without_max_win) if without_max_win else 0.0

    wins_wo = [x for x in without_max_win if x["pnl"] > 0]
    losses_wo = [x for x in without_max_win if x["pnl"] < 0]

    gp_wo = sum(x["pnl"] for x in wins_wo)
    gl_wo = abs(sum(x["pnl"] for x in losses_wo))
    pf_wo = gp_wo / gl_wo if gl_wo else None

    print()
    print("=== USD OUTLIER CHECK ===")
    print(f"median_pnl={median_pnl:.6f}")
    print(f"max_win={max_win:.6f}")
    print(f"max_loss={max_loss:.6f}")
    print(f"net_pnl_without_max_win={net_without_max:.6f}")
    print(f"expectancy_without_max_win={expectancy_without_max:.6f}")

    if pf_wo is None:
        print("profit_factor_without_max_win=INF")
    else:
        print(f"profit_factor_without_max_win={pf_wo:.6f}")

# Русский комментарий: сохраняем итог edge validation в PostgreSQL для scorecard/dashboard.
def classify_edge_status() -> str:
    if trades < 100:
        return "INSUFFICIENT_SAMPLE"

    if (
        (profit_factor is not None and profit_factor > 1.0)
        and pf_wo is not None
        and pf_wo > 1.0
        and expectancy_without_max > 0
        and median_pnl > 0
    ):
        return "EDGE_CONFIRMED_V1"

    if (
        pf_wo is not None
        and pf_wo > 0.95
        and expectancy_without_max > -1e-9
    ):
        return "EDGE_WEAK"

    return "EDGE_REJECTED"


status = classify_edge_status()

with psycopg.connect(DATABASE_URL) as conn:
    conn.execute(
        """
        INSERT INTO analytics_edge_validation_metrics_v1 (
            symbol,
            closed_trades,
            wins,
            losses,
            winrate,
            net_pnl,
            profit_factor,
            expectancy,
            median_pnl,
            max_win,
            max_loss,
            net_pnl_without_max_win,
            expectancy_without_max_win,
            profit_factor_without_max_win,
            status,
            calculated_at
        )
        VALUES (
            %(symbol)s,
            %(closed_trades)s,
            %(wins)s,
            %(losses)s,
            %(winrate)s,
            %(net_pnl)s,
            %(profit_factor)s,
            %(expectancy)s,
            %(median_pnl)s,
            %(max_win)s,
            %(max_loss)s,
            %(net_pnl_without_max_win)s,
            %(expectancy_without_max_win)s,
            %(profit_factor_without_max_win)s,
            %(status)s,
            now()
        )
        ON CONFLICT (symbol) DO UPDATE SET
            closed_trades = EXCLUDED.closed_trades,
            wins = EXCLUDED.wins,
            losses = EXCLUDED.losses,
            winrate = EXCLUDED.winrate,
            net_pnl = EXCLUDED.net_pnl,
            profit_factor = EXCLUDED.profit_factor,
            expectancy = EXCLUDED.expectancy,
            median_pnl = EXCLUDED.median_pnl,
            max_win = EXCLUDED.max_win,
            max_loss = EXCLUDED.max_loss,
            net_pnl_without_max_win = EXCLUDED.net_pnl_without_max_win,
            expectancy_without_max_win = EXCLUDED.expectancy_without_max_win,
            profit_factor_without_max_win = EXCLUDED.profit_factor_without_max_win,
            status = EXCLUDED.status,
            calculated_at = now();
        """,
        {
            "symbol": SYMBOL,
            "closed_trades": trades,
            "wins": len(wins),
            "losses": len(losses),
            "winrate": winrate,
            "net_pnl": net_pnl,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "median_pnl": median_pnl,
            "max_win": max_win,
            "max_loss": max_loss,
            "net_pnl_without_max_win": net_without_max,
            "expectancy_without_max_win": expectancy_without_max,
            "profit_factor_without_max_win": pf_wo,
            "status": status,
        },
    )
    conn.commit()

print()
print("=== EDGE VALIDATION STATUS ===")
print(f"status={status}")
print("persisted=1")
