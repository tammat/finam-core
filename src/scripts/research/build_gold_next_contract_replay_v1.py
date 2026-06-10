#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import timezone, timedelta

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SYMBOLS = [
    s.strip()
    for s in os.getenv("GOLD_REPLAY_SYMBOLS", "GDM6@RTSX,GDU6@RTSX").split(",")
    if s.strip()
]

TIMEFRAME = os.getenv("GOLD_TIMEFRAME", "M5")
EXIT_BARS = int(os.getenv("GOLD_EXIT_BARS", "10"))
HOURS = {int(x) for x in os.getenv("GOLD_HOURS_MSK", "15,16,17,18").split(",") if x.strip()}

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
        "gross_profit": round(gp, 6),
        "gross_loss": round(gl, 6),
        "max_drawdown": round(max_dd, 6),
        "best_trade": round(max(wins), 6) if wins else 0,
        "worst_trade": round(min(losses), 6) if losses else 0,
    }

def status(m: dict) -> str:
    pf = m["profit_factor"]
    if m["trades"] < 50:
        return "LOW_SAMPLE"
    if m["expectancy"] > 3 and pf is not None and pf >= 2.0:
        return "STRONG_TRANSFER"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.5:
        return "TRANSFER_CONFIRMED"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.1:
        return "WEAK_TRANSFER"
    return "TRANSFER_NOT_CONFIRMED"

def run_symbol(cur, symbol: str) -> dict:
    cur.execute(SQL, (symbol, TIMEFRAME))
    rows = [dict(r) for r in cur.fetchall()]

    closes = [float(r["close"]) for r in rows if r["close"] is not None]
    timestamps = [r["ts"] for r in rows if r["close"] is not None]

    pnl_values: list[float] = []

    for i in range(20, len(closes) - EXIT_BARS):
        hour_msk = timestamps[i].astimezone(MSK).hour
        if hour_msk not in HOURS:
            continue

        mean20 = sum(closes[i - 20:i]) / 20.0
        entry = closes[i]
        exit_price = closes[i + EXIT_BARS]

        # Русский комментарий: проверяем переносимость утверждённого GOLD SHORT ONLY профиля на следующий контракт.
        if entry < mean20 * 0.998:
            pnl_values.append(entry - exit_price)

    m = metrics(pnl_values)
    m["symbol"] = symbol
    m["bars"] = len(closes)
    m["status"] = status(m)
    return m

def main() -> None:
    print("=== GOLD NEXT CONTRACT REPLAY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbols={','.join(SYMBOLS)}")
    print(f"timeframe={TIMEFRAME}")
    print("direction=SHORT_ONLY")
    print(f"hours_msk={','.join(str(x) for x in sorted(HOURS))}")
    print(f"exit_bars={EXIT_BARS}")
    print()

    results = []

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol in SYMBOLS:
                results.append(run_symbol(cur, symbol))

    print("NEXT_CONTRACT_ROWS")

    for m in results:
        print(
            "NEXT_CONTRACT_ROW "
            f"symbol={m['symbol']} "
            f"bars={m['bars']} "
            f"trades={m['trades']} "
            f"wins={m['wins']} "
            f"losses={m['losses']} "
            f"net_pnl={m['net_pnl']} "
            f"expectancy={m['expectancy']} "
            f"winrate={m['winrate']} "
            f"profit_factor={m['profit_factor']} "
            f"gross_profit={m['gross_profit']} "
            f"gross_loss={m['gross_loss']} "
            f"max_drawdown={m['max_drawdown']} "
            f"best_trade={m['best_trade']} "
            f"worst_trade={m['worst_trade']} "
            f"status={m['status']}"
        )

    base = next((m for m in results if m["symbol"].startswith("GDM6")), None)
    nextc = next((m for m in results if m["symbol"].startswith("GDU6")), None)

    print()

    if base and nextc:
        base_pf = base["profit_factor"] or 0
        next_pf = nextc["profit_factor"] or 0
        pf_ratio = round(next_pf / base_pf, 6) if base_pf else None
        exp_ratio = round(nextc["expectancy"] / base["expectancy"], 6) if base["expectancy"] else None

        print(
            "TRANSFER_ROW "
            f"base_symbol={base['symbol']} "
            f"next_symbol={nextc['symbol']} "
            f"base_pf={base['profit_factor']} "
            f"next_pf={nextc['profit_factor']} "
            f"pf_ratio={pf_ratio} "
            f"base_expectancy={base['expectancy']} "
            f"next_expectancy={nextc['expectancy']} "
            f"expectancy_ratio={exp_ratio} "
            f"next_status={nextc['status']}"
        )

        if nextc["status"] in {"STRONG_TRANSFER", "TRANSFER_CONFIRMED"}:
            verdict = "GOLD_EDGE_TRANSFER_CONFIRMED"
        elif nextc["status"] == "WEAK_TRANSFER":
            verdict = "GOLD_EDGE_TRANSFER_WEAK"
        else:
            verdict = "GOLD_EDGE_TRANSFER_NOT_CONFIRMED"
    else:
        verdict = "GOLD_EDGE_TRANSFER_INCOMPLETE"

    print(f"VERDICT={verdict}")
    print("GOLD_NEXT_CONTRACT_REPLAY_V1_OK")

if __name__ == "__main__":
    main()
