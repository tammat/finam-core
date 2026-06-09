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

KEEP_SESSIONS = {
    x.strip()
    for x in os.getenv("GOLD_KEEP_SESSIONS", "вечерняя_сессия").split(",")
    if x.strip()
}

AVOID_SESSIONS = {
    x.strip()
    for x in os.getenv("GOLD_AVOID_SESSIONS", "утро_раннее,поздняя_сессия").split(",")
    if x.strip()
}

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
        "gross_profit": round(gross_profit, 6),
        "gross_loss": round(gross_loss, 6),
    }

def status(m: dict) -> str:
    pf = m["profit_factor"]
    if m["trades"] < 20:
        return "NO_DATA"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.50:
        return "STRONG_FILTER"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.20:
        return "POSITIVE_FILTER"
    if m["expectancy"] <= 0:
        return "REJECT"
    return "WATCH"

def fmt(label: str, m: dict) -> str:
    return (
        f"{label}_ROW "
        f"trades={m['trades']} "
        f"wins={m['wins']} "
        f"losses={m['losses']} "
        f"net_pnl={m['net_pnl']} "
        f"expectancy={m['expectancy']} "
        f"winrate={m['winrate']} "
        f"profit_factor={m['profit_factor']} "
        f"gross_profit={m['gross_profit']} "
        f"gross_loss={m['gross_loss']} "
        f"status={status(m)}"
    )

def main() -> None:
    print("=== GOLD SHORT ONLY SESSION FILTER EFFECTIVENESS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"timeframe={TIMEFRAME}")
    print(f"exit_bars={EXIT_BARS}")
    print(f"keep_sessions={','.join(sorted(KEEP_SESSIONS))}")
    print(f"avoid_sessions={','.join(sorted(AVOID_SESSIONS))}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, TIMEFRAME))
            rows = list(cur.fetchall())

    closes = [float(r["close"]) for r in rows if r["close"] is not None]
    timestamps = [r["ts"] for r in rows if r["close"] is not None]

    all_pnl: list[float] = []
    keep_pnl: list[float] = []
    avoid_pnl: list[float] = []
    neutral_pnl: list[float] = []

    for i in range(20, len(closes) - EXIT_BARS):
        mean20 = sum(closes[i - 20:i]) / 20.0
        entry = closes[i]
        exit_price = closes[i + EXIT_BARS]

        if entry < mean20 * 0.998:
            pnl = entry - exit_price
            hour = timestamps[i].astimezone(MSK).hour
            sess = session_bucket(hour)

            all_pnl.append(pnl)

            if sess in KEEP_SESSIONS:
                keep_pnl.append(pnl)
            elif sess in AVOID_SESSIONS:
                avoid_pnl.append(pnl)
            else:
                neutral_pnl.append(pnl)

    all_m = metrics(all_pnl)
    keep_m = metrics(keep_pnl)
    avoid_m = metrics(avoid_pnl)
    neutral_m = metrics(neutral_pnl)

    print("FILTER_EFFECTIVENESS_ROWS")
    print(fmt("ALL", all_m))
    print(fmt("KEEP", keep_m))
    print(fmt("AVOID", avoid_m))
    print(fmt("NEUTRAL", neutral_m))
    print()

    expectancy_delta = round(keep_m["expectancy"] - all_m["expectancy"], 6)
    net_delta = round(keep_m["net_pnl"] - all_m["net_pnl"], 6)

    print(
        "EFFECTIVENESS_ROW "
        f"expectancy_delta_keep_vs_all={expectancy_delta} "
        f"net_delta_keep_vs_all={net_delta} "
        f"removed_trades={all_m['trades'] - keep_m['trades']} "
        f"removed_avoid_trades={avoid_m['trades']} "
        f"removed_avoid_net_pnl={avoid_m['net_pnl']}"
    )

    print()

    if keep_m["expectancy"] > all_m["expectancy"] and keep_m["profit_factor"] and keep_m["profit_factor"] > all_m["profit_factor"]:
        verdict = "SESSION_FILTER_IMPROVES_EDGE"
    else:
        verdict = "SESSION_FILTER_NOT_CONFIRMED"

    print(f"VERDICT={verdict}")
    print("GOLD_SHORT_ONLY_SESSION_FILTER_EFFECTIVENESS_V1_OK")

if __name__ == "__main__":
    main()
