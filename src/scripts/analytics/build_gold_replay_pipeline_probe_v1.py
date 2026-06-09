#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SYMBOL = os.getenv("GOLD_REPLAY_SYMBOL", "GDM6@RTSX")
TIMEFRAME = os.getenv("GOLD_REPLAY_TIMEFRAME", "M5")
LIMIT_BARS = int(os.getenv("GOLD_REPLAY_LIMIT_BARS", "5000"))

SQL = """
SELECT
    ts,
    open,
    high,
    low,
    close,
    volume
FROM market_bars
WHERE symbol = %s
  AND timeframe = %s
ORDER BY ts ASC
LIMIT %s;
"""

def main() -> None:
    print("=== GOLD REPLAY PIPELINE PROBE V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print(f"limit_bars={LIMIT_BARS}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, TIMEFRAME, LIMIT_BARS))
            rows = [dict(r) for r in cur.fetchall()]

    bars = len(rows)

    if bars == 0:
        print("PROBE_ROWS")
        print("NONE")
        print()
        print("bars=0")
        print("signals=0")
        print("VERDICT=NO_BARS")
        print("GOLD_REPLAY_PIPELINE_PROBE_V1_OK")
        return

    closes = [float(r["close"]) for r in rows if r["close"] is not None]

    signals = 0
    long_signals = 0
    short_signals = 0

    # Русский комментарий: минимальный research-only probe.
    # Не стратегия. Проверяет, что баровый цикл и расчёт признаков по золоту исполнимы.
    for i in range(20, len(closes)):
        window = closes[i - 20:i]
        mean = sum(window) / len(window)
        current = closes[i]

        if current > mean * 1.002:
            signals += 1
            long_signals += 1
        elif current < mean * 0.998:
            signals += 1
            short_signals += 1

    first_ts = rows[0]["ts"]
    last_ts = rows[-1]["ts"]

    print("PROBE_ROWS")
    print(
        "PROBE_ROW "
        f"symbol={SYMBOL} "
        f"timeframe={TIMEFRAME} "
        f"bars={bars} "
        f"first_ts={first_ts} "
        f"last_ts={last_ts} "
        f"signals={signals} "
        f"long_signals={long_signals} "
        f"short_signals={short_signals}"
    )

    print()
    print(f"bars={bars}")
    print(f"signals={signals}")
    print(f"long_signals={long_signals}")
    print(f"short_signals={short_signals}")

    if bars >= 1000 and signals > 0:
        verdict = "REPLAY_PROBE_READY"
    elif bars >= 100:
        verdict = "REPLAY_PROBE_LIMITED"
    else:
        verdict = "REPLAY_PROBE_INSUFFICIENT"

    print(f"VERDICT={verdict}")
    print("GOLD_REPLAY_PIPELINE_PROBE_V1_OK")

if __name__ == "__main__":
    main()
