#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SYMBOLS = [
    s.strip()
    for s in os.getenv("GOLD_SHORT_SYMBOLS", "GDM6@RTSX,GDU6@RTSX").split(",")
    if s.strip()
]

TIMEFRAME = os.getenv("GOLD_TIMEFRAME", "M5")

EXIT_BARS_LIST = [
    int(x.strip())
    for x in os.getenv("GOLD_EXIT_BARS_LIST", "3,5,8,10,15").split(",")
    if x.strip()
]

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
    trades = len(values)

    pf = None
    if gross_loss > 0:
        pf = round(gross_profit / gross_loss, 4)

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

def status(m: dict) -> str:
    pf = m["profit_factor"]
    if m["trades"] < 100:
        return "NO_DATA"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.20:
        return "STRONG"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.05:
        return "WEAK_POSITIVE"
    if m["expectancy"] > 0:
        return "WATCH"
    return "REJECT"

def main() -> None:
    print("=== GOLD SHORT ONLY EXIT SENSITIVITY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbols={','.join(SYMBOLS)}")
    print(f"timeframe={TIMEFRAME}")
    print(f"exit_bars_list={','.join(map(str, EXIT_BARS_LIST))}")
    print()

    all_rows = []

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol in SYMBOLS:
                cur.execute(SQL, (symbol, TIMEFRAME))
                rows = list(cur.fetchall())

                closes = [float(r["close"]) for r in rows if r["close"] is not None]

                for exit_bars in EXIT_BARS_LIST:
                    short_pnl: list[float] = []

                    for i in range(20, len(closes) - exit_bars):
                        mean20 = sum(closes[i - 20:i]) / 20.0
                        entry = closes[i]
                        exit_price = closes[i + exit_bars]

                        # Русский комментарий: только SHORT-ветка baseline-сигнала.
                        if entry < mean20 * 0.998:
                            short_pnl.append(entry - exit_price)

                    m = metrics(short_pnl)
                    m["symbol"] = symbol
                    m["bars"] = len(closes)
                    m["exit_bars"] = exit_bars
                    m["status"] = status(m)
                    all_rows.append(m)

    print("SENSITIVITY_ROWS")

    strong = 0
    weak_positive = 0
    reject = 0

    for m in all_rows:
        if m["status"] == "STRONG":
            strong += 1
        elif m["status"] in {"WEAK_POSITIVE", "WATCH"}:
            weak_positive += 1
        elif m["status"] == "REJECT":
            reject += 1

        print(
            "SENSITIVITY_ROW "
            f"symbol={m['symbol']} "
            f"timeframe={TIMEFRAME} "
            f"exit_bars={m['exit_bars']} "
            f"bars={m['bars']} "
            f"trades={m['trades']} "
            f"net_pnl={m['net_pnl']} "
            f"expectancy={m['expectancy']} "
            f"winrate={m['winrate']} "
            f"profit_factor={m['profit_factor']} "
            f"max_win={m['max_win']} "
            f"max_loss={m['max_loss']} "
            f"status={m['status']}"
        )

    print()
    print(f"STRONG_ROWS={strong}")
    print(f"WEAK_POSITIVE_ROWS={weak_positive}")
    print(f"REJECT_ROWS={reject}")
    print(f"TOTAL_ROWS={len(all_rows)}")

    if strong >= 2 and reject == 0:
        verdict = "GOLD_SHORT_EDGE_STABLE"
    elif strong >= 1 and reject <= 1:
        verdict = "GOLD_SHORT_EDGE_PARTIAL"
    else:
        verdict = "GOLD_SHORT_EDGE_UNSTABLE"

    print(f"VERDICT={verdict}")
    print("GOLD_SHORT_ONLY_EXIT_SENSITIVITY_V1_OK")

if __name__ == "__main__":
    main()
