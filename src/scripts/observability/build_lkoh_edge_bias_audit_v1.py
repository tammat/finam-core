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

    if side == "BUY":
        open_buys.append({"qty": qty, "price": price, "ts": ts})
        continue

    if side == "SELL":
        remaining = qty

        while remaining > 0 and open_buys:
            b = open_buys[0]
            matched = min(remaining, b["qty"])
            pnl = (price - b["price"]) * matched

            entry_ts = b["ts"]
            hour_msk = (int(entry_ts.strftime("%H")) + 3) % 24
            date_msk = entry_ts.astimezone().date().isoformat()

            closed.append(
                {
                    "entry_ts": entry_ts,
                    "exit_ts": ts,
                    "qty": matched,
                    "entry": b["price"],
                    "exit": price,
                    "pnl": pnl,
                    "hour_msk": hour_msk,
                    "weekday": entry_ts.strftime("%A"),
                    "date_msk": date_msk,
                }
            )

            b["qty"] -= matched
            remaining -= matched

            if b["qty"] <= 1e-12:
                open_buys.popleft()

by_date = defaultdict(list)
by_weekday = defaultdict(list)
by_hour = defaultdict(list)
by_date_hour = defaultdict(list)

for t in closed:
    by_date[t["date_msk"]].append(t["pnl"])
    by_weekday[t["weekday"]].append(t["pnl"])
    by_hour[t["hour_msk"]].append(t["pnl"])
    by_date_hour[(t["date_msk"], t["hour_msk"])].append(t["pnl"])

total = len(closed)

print("=== LKOH EDGE BIAS AUDIT V1 ===")
print()
print(f"symbol={SYMBOL}")
print(f"closed_trades={total}")
print()

print("=== КОНЦЕНТРАЦИЯ ПО ДАТАМ ===")
print("date        trades  share    net_pnl      pf        expectancy")

date_rows = []

for d, pnls in sorted(by_date.items()):
    trades, winrate, net_pnl, pf, expectancy = calc_stats(pnls)
    share = trades / total * 100 if total else 0
    date_rows.append((d, trades, share, net_pnl, pf, expectancy))

for d, trades, share, net_pnl, pf, expectancy in sorted(date_rows, key=lambda x: x[1], reverse=True):
    pf_text = "INF" if pf is None else f"{pf:.4f}"
    print(
        f"{d:<10}  "
        f"{trades:>6}  "
        f"{share:>5.1f}%  "
        f"{net_pnl:>9.4f}  "
        f"{pf_text:>8}  "
        f"{expectancy:>10.4f}"
    )

print()
print("=== КОНЦЕНТРАЦИЯ ПО ДНЯМ НЕДЕЛИ ===")
print("weekday     trades  share    net_pnl      pf        expectancy")

weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

for weekday in weekday_order:
    if weekday not in by_weekday:
        continue

    pnls = by_weekday[weekday]
    trades, winrate, net_pnl, pf, expectancy = calc_stats(pnls)
    share = trades / total * 100 if total else 0
    pf_text = "INF" if pf is None else f"{pf:.4f}"

    print(
        f"{weekday:<10}  "
        f"{trades:>6}  "
        f"{share:>5.1f}%  "
        f"{net_pnl:>9.4f}  "
        f"{pf_text:>8}  "
        f"{expectancy:>10.4f}"
    )

print()
print("=== КОНЦЕНТРАЦИЯ ПО ЧАСАМ МСК ===")
print("hour  trades  share    net_pnl      pf        expectancy")

for hour in sorted(by_hour):
    pnls = by_hour[hour]
    trades, winrate, net_pnl, pf, expectancy = calc_stats(pnls)
    share = trades / total * 100 if total else 0
    pf_text = "INF" if pf is None else f"{pf:.4f}"

    print(
        f"{hour:>4}  "
        f"{trades:>6}  "
        f"{share:>5.1f}%  "
        f"{net_pnl:>9.4f}  "
        f"{pf_text:>8}  "
        f"{expectancy:>10.4f}"
    )

print()
print("=== ТОП ДАТА+ЧАС ПО КОНЦЕНТРАЦИИ ===")
print("date        hour  trades  share    net_pnl      pf        expectancy")

combo_rows = []

for key, pnls in by_date_hour.items():
    d, h = key
    trades, winrate, net_pnl, pf, expectancy = calc_stats(pnls)
    share = trades / total * 100 if total else 0
    combo_rows.append((d, h, trades, share, net_pnl, pf, expectancy))

for d, h, trades, share, net_pnl, pf, expectancy in sorted(combo_rows, key=lambda x: x[2], reverse=True)[:20]:
    pf_text = "INF" if pf is None else f"{pf:.4f}"
    print(
        f"{d:<10}  "
        f"{h:>4}  "
        f"{trades:>6}  "
        f"{share:>5.1f}%  "
        f"{net_pnl:>9.4f}  "
        f"{pf_text:>8}  "
        f"{expectancy:>10.4f}"
    )

largest_date_share = max((r[2] for r in date_rows), default=0)
largest_weekday_share = max((len(v) / total * 100 for v in by_weekday.values()), default=0)
largest_hour_share = max((len(v) / total * 100 for v in by_hour.values()), default=0)
largest_combo_share = max((r[3] for r in combo_rows), default=0)

print()
print("=== BIAS VERDICT ===")

flags = []

if largest_date_share >= 50:
    flags.append("DATE_CONCENTRATION")

if largest_weekday_share >= 70:
    flags.append("WEEKDAY_CONCENTRATION")

if largest_hour_share >= 50:
    flags.append("HOUR_CONCENTRATION")

if largest_combo_share >= 35:
    flags.append("DATE_HOUR_CONCENTRATION")

if flags:
    status = "EDGE_SUSPICIOUS"
    reason = ",".join(flags)
else:
    status = "EDGE_BIAS_NOT_DETECTED"
    reason = "distribution_not_overconcentrated"

print(f"status={status}")
print(f"reason={reason}")

# Русский комментарий: сохраняем результат bias-аудита для Edge Scorecard.
with psycopg.connect(DATABASE_URL) as conn:
    conn.execute(
        """
        INSERT INTO analytics_edge_bias_audit_v1 (
            symbol,
            bias_status,
            bias_reason,
            calculated_at
        )
        VALUES (
            %(symbol)s,
            %(bias_status)s,
            %(bias_reason)s,
            now()
        )
        ON CONFLICT (symbol) DO UPDATE SET
            bias_status = EXCLUDED.bias_status,
            bias_reason = EXCLUDED.bias_reason,
            calculated_at = now();
        """,
        {
            "symbol": SYMBOL,
            "bias_status": status,
            "bias_reason": reason,
        },
    )
    conn.commit()

print("persisted=1")
