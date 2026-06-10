#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import timezone, timedelta

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SYMBOLS = [
    s.strip()
    for s in os.getenv("BR_SYMBOLS", "BRM6@RTSX,BRN6@RTSX").split(",")
    if s.strip()
]

MSK = timezone(timedelta(hours=3))

SQL = """
SELECT
    symbol,
    net_pnl,
    COALESCE(exit_ts, closed_at, created_at) AS ts
FROM closed_trades
WHERE symbol = ANY(%s)
ORDER BY ts;
"""

VARIANTS = {
    "ALL_BR": None,
    "KEEP_09_13": set(range(9, 14)),
    "KEEP_10_13": set(range(10, 14)),
    "KEEP_09_14": set(range(9, 15)),
    "EXCLUDE_17_18": "exclude_17_18",
    "KEEP_09_13_EXCLUDE_17_18": set(range(9, 14)),
}

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

def status(m: dict) -> str:
    pf = m["profit_factor"]
    if m["trades"] < 30:
        return "LOW_SAMPLE"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.5:
        return "STRONG_REVALIDATED"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.2:
        return "REVALIDATED"
    if m["expectancy"] > 0:
        return "WATCH"
    return "REJECT"

def include_variant(name: str, hour: int) -> bool:
    rule = VARIANTS[name]

    if rule is None:
        return True

    if rule == "exclude_17_18":
        return hour not in {17, 18}

    if isinstance(rule, set):
        return hour in rule

    return False

def main() -> None:
    print("=== BR RUNTIME TIME FILTER REVALIDATION V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbols={','.join(SYMBOLS)}")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOLS,))
            rows = [dict(r) for r in cur.fetchall()]

    variant_pnl = {name: [] for name in VARIANTS}
    by_symbol_variant = {}

    for r in rows:
        ts = r["ts"]
        if ts is None:
            continue

        symbol = r["symbol"]
        pnl = float(r["net_pnl"] or 0)
        hour = ts.astimezone(MSK).hour

        for name in VARIANTS:
            if include_variant(name, hour):
                variant_pnl[name].append(pnl)
                by_symbol_variant.setdefault((symbol, name), []).append(pnl)

    print("VARIANT_ROWS")

    best_name = None
    best_score = None

    for name, values in variant_pnl.items():
        m = metrics(values)

        # Русский комментарий: score учитывает expectancy и минимальную устойчивость выборки.
        score = m["expectancy"] * min(m["trades"], 100)

        print(
            "VARIANT_ROW "
            f"variant={name} "
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
            f"score={round(score,6)} "
            f"status={status(m)}"
        )

        if best_score is None or score > best_score:
            best_score = score
            best_name = name

    print()
    print("CONTRACT_VARIANT_ROWS")

    for (symbol, name), values in sorted(by_symbol_variant.items()):
        m = metrics(values)
        print(
            "CONTRACT_VARIANT_ROW "
            f"symbol={symbol} "
            f"variant={name} "
            f"trades={m['trades']} "
            f"net_pnl={m['net_pnl']} "
            f"expectancy={m['expectancy']} "
            f"profit_factor={m['profit_factor']} "
            f"status={status(m)}"
        )

    print()
    print(f"BEST_VARIANT name={best_name} score={round(best_score or 0,6)}")

    best_m = metrics(variant_pnl[best_name]) if best_name else {"trades": 0, "expectancy": 0, "profit_factor": None}
    if status(best_m) in {"STRONG_REVALIDATED", "REVALIDATED"}:
        verdict = "BR_TIME_FILTER_REVALIDATED"
    elif status(best_m) == "WATCH":
        verdict = "BR_TIME_FILTER_WATCH"
    else:
        verdict = "BR_TIME_FILTER_NOT_CONFIRMED"

    print(f"VERDICT={verdict}")
    print("BR_RUNTIME_TIME_FILTER_REVALIDATION_V1_OK")

if __name__ == "__main__":
    main()
