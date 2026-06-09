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
    if m["trades"] < 100:
        return "NO_DATA"
    pf = m["profit_factor"]
    if m["expectancy"] > 0 and pf is not None and pf > 1.15:
        return "SHORT_CANDIDATE"
    if m["expectancy"] > 0:
        return "WATCH"
    return "REJECT"

def main() -> None:
    print("=== GOLD SHORT ONLY RESEARCH V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbols={','.join(SYMBOLS)}")
    print(f"timeframe={TIMEFRAME}")
    print(f"exit_bars={EXIT_BARS}")
    print()

    results = []

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol in SYMBOLS:
                cur.execute(SQL, (symbol, TIMEFRAME))
                rows = list(cur.fetchall())

                closes = [float(r["close"]) for r in rows if r["close"] is not None]

                short_pnl: list[float] = []

                for i in range(20, len(closes) - EXIT_BARS):
                    mean20 = sum(closes[i - 20:i]) / 20.0
                    entry = closes[i]
                    exit_price = closes[i + EXIT_BARS]

                    # Русский комментарий: исследуем только SHORT-ветку baseline-логики.
                    if entry < mean20 * 0.998:
                        short_pnl.append(entry - exit_price)

                m = metrics(short_pnl)
                m["symbol"] = symbol
                m["bars"] = len(closes)
                m["status"] = status(m)
                results.append(m)

    print("SHORT_ONLY_ROWS")

    for m in results:
        print(
            "SHORT_ONLY_ROW "
            f"symbol={m['symbol']} "
            f"timeframe={TIMEFRAME} "
            f"bars={m['bars']} "
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
            f"gross_loss={m['gross_loss']} "
            f"status={m['status']}"
        )

    candidates = [m for m in results if m["status"] == "SHORT_CANDIDATE"]

    print()
    print(f"CANDIDATES={len(candidates)}")
    print(f"ROWS={len(results)}")

    if candidates:
        verdict = "GOLD_SHORT_ONLY_CANDIDATE_CONFIRMED"
    else:
        verdict = "GOLD_SHORT_ONLY_NOT_CONFIRMED"

    print(f"VERDICT={verdict}")
    print("GOLD_SHORT_ONLY_RESEARCH_V1_OK")

if __name__ == "__main__":
    main()
