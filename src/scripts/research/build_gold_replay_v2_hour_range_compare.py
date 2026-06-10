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

RANGES = {
    "HOUR_16": {16},
    "HOURS_15_18": {15, 16, 17, 18},
    "EVENING_14_18": {14, 15, 16, 17, 18},
    "WIDE_13_18": {13, 14, 15, 16, 17, 18},
}

MSK = timezone(timedelta(hours=3))

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

    gp = sum(wins)
    gl = abs(sum(losses))
    net = sum(values)
    trades = len(values)

    equity = 0.0
    peak = 0.0
    max_dd = 0.0

    for pnl in values:
        equity += pnl
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": round(net, 6),
        "expectancy": round(net / trades, 6) if trades else 0,
        "winrate": round(100.0 * len(wins) / trades, 2) if trades else 0,
        "profit_factor": round(gp / gl, 4) if gl > 0 else None,
        "max_drawdown": round(max_dd, 6),
        "best_trade": round(max(wins), 6) if wins else 0,
        "worst_trade": round(min(losses), 6) if losses else 0,
    }

def main() -> None:
    print("=== GOLD REPLAY V2 HOUR RANGE COMPARE ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print("direction=SHORT_ONLY")
    print(f"exit_bars={EXIT_BARS}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, TIMEFRAME))
            rows = [dict(r) for r in cur.fetchall()]

    closes = [float(r["close"]) for r in rows if r["close"] is not None]
    timestamps = [r["ts"] for r in rows if r["close"] is not None]

    result = {name: [] for name in RANGES}

    for i in range(20, len(closes) - EXIT_BARS):
        hour = timestamps[i].astimezone(MSK).hour
        mean20 = sum(closes[i - 20:i]) / 20.0
        entry = closes[i]
        exit_price = closes[i + EXIT_BARS]

        # Русский комментарий: сравниваем только подтверждённый SHORT-кандидат по разным временным окнам.
        if entry < mean20 * 0.998:
            pnl = entry - exit_price

            for name, hours in RANGES.items():
                if hour in hours:
                    result[name].append(pnl)

    print("RANGE_ROWS")

    best_name = None
    best_score = None

    for name, values in result.items():
        m = metrics(values)

        # Русский комментарий: score учитывает expectancy и минимальную устойчивость выборки.
        score = (m["expectancy"] or 0) * min(m["trades"], 100)

        print(
            "RANGE_ROW "
            f"range={name} "
            f"hours={','.join(str(x) for x in sorted(RANGES[name]))} "
            f"trades={m['trades']} "
            f"wins={m['wins']} "
            f"losses={m['losses']} "
            f"net_pnl={m['net_pnl']} "
            f"expectancy={m['expectancy']} "
            f"winrate={m['winrate']} "
            f"profit_factor={m['profit_factor']} "
            f"max_drawdown={m['max_drawdown']} "
            f"best_trade={m['best_trade']} "
            f"worst_trade={m['worst_trade']} "
            f"score={round(score, 6)}"
        )

        if best_score is None or score > best_score:
            best_score = score
            best_name = name

    print()
    print(f"BEST_RANGE name={best_name} score={round(best_score or 0, 6)}")
    print("VERDICT=GOLD_REPLAY_V2_HOUR_RANGE_COMPARED")
    print("GOLD_REPLAY_V2_HOUR_RANGE_COMPARE_OK")

if __name__ == "__main__":
    main()
