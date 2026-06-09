#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SYMBOL = os.getenv("GOLD_SYMBOL", "GDM6@RTSX")
TIMEFRAME = os.getenv("GOLD_TIMEFRAME", "M5")
EXIT_BARS = int(os.getenv("GOLD_EXIT_BARS", "5"))

SQL = """
SELECT ts, close
FROM market_bars
WHERE symbol = %s
  AND timeframe = %s
ORDER BY ts;
"""

def metrics(values: list[float]) -> dict:
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x <= 0]

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    net = sum(values)

    pf = None
    if gross_loss > 0:
        pf = round(gross_profit / gross_loss, 4)

    trades = len(values)
    expectancy = net / trades if trades else 0.0
    winrate = 100.0 * len(wins) / trades if trades else 0.0

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": round(net, 6),
        "expectancy": round(expectancy, 6),
        "winrate": round(winrate, 2),
        "profit_factor": pf,
        "max_win": round(max(wins), 6) if wins else 0,
        "max_loss": round(min(losses), 6) if losses else 0,
        "gross_profit": round(gross_profit, 6),
        "gross_loss": round(gross_loss, 6),
    }

def row(label: str, m: dict) -> str:
    return (
        f"{label}_ROW "
        f"trades={m['trades']} "
        f"wins={m['wins']} "
        f"losses={m['losses']} "
        f"net_pnl={m['net_pnl']} "
        f"expectancy={m['expectancy']} "
        f"winrate={m['winrate']} "
        f"profit_factor={m['profit_factor']} "
        f"max_win={m['max_win']} "
        f"max_loss={m['max_loss']} "
        f"gross_profit={m['gross_profit']} "
        f"gross_loss={m['gross_loss']}"
    )

def main() -> None:
    print("=== GOLD BASELINE SIGNAL RESEARCH V2 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print(f"exit_bars={EXIT_BARS}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, TIMEFRAME))
            rows = list(cur.fetchall())

    closes = [float(r["close"]) for r in rows if r["close"] is not None]

    long_pnl: list[float] = []
    short_pnl: list[float] = []

    for i in range(20, len(closes) - EXIT_BARS):
        mean20 = sum(closes[i - 20:i]) / 20.0
        entry = closes[i]
        exit_price = closes[i + EXIT_BARS]

        if entry > mean20 * 1.002:
            long_pnl.append(exit_price - entry)
        elif entry < mean20 * 0.998:
            short_pnl.append(entry - exit_price)

    long_m = metrics(long_pnl)
    short_m = metrics(short_pnl)
    all_m = metrics(long_pnl + short_pnl)

    print(row("ALL", all_m))
    print(row("LONG", long_m))
    print(row("SHORT", short_m))
    print()

    if long_m["expectancy"] > short_m["expectancy"]:
        best_side = "LONG"
        edge_delta = round(long_m["expectancy"] - short_m["expectancy"], 6)
    elif short_m["expectancy"] > long_m["expectancy"]:
        best_side = "SHORT"
        edge_delta = round(short_m["expectancy"] - long_m["expectancy"], 6)
    else:
        best_side = "BALANCED"
        edge_delta = 0.0

    print(
        "COMPARISON_ROW "
        f"best_side={best_side} "
        f"edge_delta={edge_delta} "
        f"long_expectancy={long_m['expectancy']} "
        f"short_expectancy={short_m['expectancy']} "
        f"long_pf={long_m['profit_factor']} "
        f"short_pf={short_m['profit_factor']}"
    )

    print()
    print("VERDICT=GOLD_BASELINE_RESEARCH_DECOMPOSED")
    print("GOLD_BASELINE_SIGNAL_RESEARCH_V2_OK")

if __name__ == "__main__":
    main()
