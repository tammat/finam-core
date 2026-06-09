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
WHERE symbol = %s
  AND timeframe = %s
ORDER BY ts;
"""

def session_bucket(hour_msk: int) -> str:
    if 7 <= hour_msk < 10:
        return "утро_раннее"
    if 10 <= hour_msk < 14:
        return "московская_середина"
    if 14 <= hour_msk < 19:
        return "вечерняя_сессия"
    if 19 <= hour_msk < 24:
        return "поздняя_сессия"
    return "ночь"

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

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": round(net, 6),
        "expectancy": round(net / trades, 6) if trades else 0,
        "winrate": round(100.0 * len(wins) / trades, 2) if trades else 0,
        "profit_factor": pf,
    }

def status(m: dict) -> str:
    pf = m["profit_factor"]
    if m["trades"] < 20:
        return "NO_DATA"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.25:
        return "FAVORABLE"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.05:
        return "WATCH"
    if m["expectancy"] <= 0:
        return "AVOID"
    return "WATCH"

def main() -> None:
    print("=== GOLD SHORT ONLY SESSION DECOMPOSITION V1 ===")
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
    timestamps = [r["ts"] for r in rows if r["close"] is not None]

    by_hour: dict[int, list[float]] = {}
    by_session: dict[str, list[float]] = {}

    for i in range(20, len(closes) - EXIT_BARS):
        mean20 = sum(closes[i - 20:i]) / 20.0
        entry = closes[i]
        exit_price = closes[i + EXIT_BARS]

        if entry < mean20 * 0.998:
            pnl = entry - exit_price
            ts = timestamps[i]
            hour = ts.astimezone(MSK).hour
            sess = session_bucket(hour)

            by_hour.setdefault(hour, []).append(pnl)
            by_session.setdefault(sess, []).append(pnl)

    print("SESSION_ROWS")
    for sess in sorted(by_session):
        m = metrics(by_session[sess])
        print(
            "SESSION_ROW "
            f"session={sess} "
            f"trades={m['trades']} "
            f"wins={m['wins']} "
            f"losses={m['losses']} "
            f"net_pnl={m['net_pnl']} "
            f"expectancy={m['expectancy']} "
            f"winrate={m['winrate']} "
            f"profit_factor={m['profit_factor']} "
            f"status={status(m)}"
        )

    print()
    print("HOUR_ROWS")
    for hour in sorted(by_hour):
        m = metrics(by_hour[hour])
        print(
            "HOUR_ROW "
            f"hour_msk={hour} "
            f"trades={m['trades']} "
            f"net_pnl={m['net_pnl']} "
            f"expectancy={m['expectancy']} "
            f"winrate={m['winrate']} "
            f"profit_factor={m['profit_factor']} "
            f"status={status(m)}"
        )

    all_pnl = []
    for values in by_session.values():
        all_pnl.extend(values)

    all_m = metrics(all_pnl)

    print()
    print(
        "TOTAL_ROW "
        f"trades={all_m['trades']} "
        f"net_pnl={all_m['net_pnl']} "
        f"expectancy={all_m['expectancy']} "
        f"winrate={all_m['winrate']} "
        f"profit_factor={all_m['profit_factor']}"
    )

    print("VERDICT=GOLD_SHORT_SESSION_DECOMPOSED")
    print("GOLD_SHORT_ONLY_SESSION_DECOMPOSITION_V1_OK")

if __name__ == "__main__":
    main()
