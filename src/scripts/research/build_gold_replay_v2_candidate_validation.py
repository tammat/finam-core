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
HOURS = {int(x) for x in os.getenv("GOLD_HOURS_MSK", "15,16,17,18").split(",") if x.strip()}

MSK = timezone(timedelta(hours=3))

SQL = """
SELECT ts, open, high, low, close, volume
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

    pf = round(gp / gl, 4) if gl > 0 else None
    expectancy = net / trades if trades else 0.0
    winrate = 100.0 * len(wins) / trades if trades else 0.0

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
        "expectancy": round(expectancy, 6),
        "winrate": round(winrate, 2),
        "profit_factor": pf,
        "gross_profit": round(gp, 6),
        "gross_loss": round(gl, 6),
        "best_trade": round(max(wins), 6) if wins else 0,
        "worst_trade": round(min(losses), 6) if losses else 0,
        "max_drawdown": round(max_dd, 6),
    }

def verdict(m: dict) -> str:
    pf = m["profit_factor"]
    if m["trades"] < 100:
        return "GOLD_REPLAY_V2_LOW_SAMPLE"
    if m["expectancy"] > 3 and pf is not None and pf >= 2.0:
        return "GOLD_REPLAY_V2_STRONG_CANDIDATE"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.5:
        return "GOLD_REPLAY_V2_CANDIDATE_CONFIRMED"
    if m["expectancy"] > 0:
        return "GOLD_REPLAY_V2_WATCH"
    return "GOLD_REPLAY_V2_REJECT"

def main() -> None:
    print("=== GOLD REPLAY V2 CANDIDATE VALIDATION ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print("direction=SHORT_ONLY")
    print(f"exit_bars={EXIT_BARS}")
    print(f"hours_msk={','.join(str(x) for x in sorted(HOURS))}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, TIMEFRAME))
            rows = [dict(r) for r in cur.fetchall()]

    closes = [float(r["close"]) for r in rows if r["close"] is not None]
    timestamps = [r["ts"] for r in rows if r["close"] is not None]

    trades = []

    for i in range(20, len(closes) - EXIT_BARS):
        hour_msk = timestamps[i].astimezone(MSK).hour
        if hour_msk not in HOURS:
            continue

        mean20 = sum(closes[i - 20:i]) / 20.0
        entry = closes[i]
        exit_price = closes[i + EXIT_BARS]

        # Русский комментарий: replay v2 проверяет только подтверждённый research-кандидат GOLD SHORT ONLY.
        if entry < mean20 * 0.998:
            pnl = entry - exit_price
            trades.append({
                "entry_ts": timestamps[i],
                "exit_ts": timestamps[i + EXIT_BARS],
                "hour_msk": hour_msk,
                "entry": entry,
                "exit": exit_price,
                "pnl": pnl,
            })

    pnl_values = [t["pnl"] for t in trades]
    m = metrics(pnl_values)
    v = verdict(m)

    print("CONFIG_ROW "
          f"symbol={SYMBOL} timeframe={TIMEFRAME} direction=SHORT_ONLY "
          f"exit_bars={EXIT_BARS} hours_msk={','.join(str(x) for x in sorted(HOURS))}")

    print(
        "RESULT_ROW "
        f"trades={m['trades']} "
        f"wins={m['wins']} "
        f"losses={m['losses']} "
        f"net_pnl={m['net_pnl']} "
        f"expectancy={m['expectancy']} "
        f"winrate={m['winrate']} "
        f"profit_factor={m['profit_factor']} "
        f"gross_profit={m['gross_profit']} "
        f"gross_loss={m['gross_loss']} "
        f"best_trade={m['best_trade']} "
        f"worst_trade={m['worst_trade']} "
        f"max_drawdown={m['max_drawdown']}"
    )

    if trades:
        print(
            "TRACE_ROW "
            f"first_entry_ts={trades[0]['entry_ts']} "
            f"last_entry_ts={trades[-1]['entry_ts']} "
            f"first_exit_ts={trades[0]['exit_ts']} "
            f"last_exit_ts={trades[-1]['exit_ts']}"
        )

    print()
    print(f"VERDICT={v}")
    print("GOLD_REPLAY_V2_CANDIDATE_VALIDATION_OK")

if __name__ == "__main__":
    main()
