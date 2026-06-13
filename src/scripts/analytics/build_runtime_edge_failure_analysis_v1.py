#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import timezone, timedelta

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]
MSK = timezone(timedelta(hours=3))

SYMBOLS = ["BRN6@RTSX", "BRM6@RTSX", "NGN6@RTSX"]

SQL = """
SELECT
    symbol,
    net_pnl,
    COALESCE(exit_ts, closed_at, created_at) AS ts
FROM closed_trades
WHERE symbol = ANY(%s)
ORDER BY ts;
"""

def root(symbol: str) -> str:
    if symbol.startswith("BR"):
        return "BR"
    if symbol.startswith("NG"):
        return "NG"
    return symbol.split("@", 1)[0]

def metrics(values: list[float]) -> dict:
    wins = [x for x in values if x > 0]
    losses = [x for x in values if x <= 0]

    gp = sum(wins)
    gl = abs(sum(losses))
    net = sum(values)
    trades = len(values)

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": round(net, 6),
        "expectancy": round(net / trades, 6) if trades else 0,
        "winrate": round(100.0 * len(wins) / trades, 2) if trades else 0,
        "profit_factor": round(gp / gl, 4) if gl > 0 else None,
    }

def status(m: dict) -> str:
    pf = m["profit_factor"]
    if m["trades"] < 10:
        return "NO_DATA"
    if m["expectancy"] > 0 and pf is not None and pf >= 1.2:
        return "FAVORABLE"
    if m["expectancy"] > 0:
        return "WATCH"
    return "FAILURE"

def print_row(prefix: str, key: str, values: list[float]) -> None:
    m = metrics(values)
    print(
        f"{prefix}_ROW "
        f"{key} "
        f"trades={m['trades']} "
        f"wins={m['wins']} "
        f"losses={m['losses']} "
        f"net_pnl={m['net_pnl']} "
        f"expectancy={m['expectancy']} "
        f"winrate={m['winrate']} "
        f"profit_factor={m['profit_factor']} "
        f"status={status(m)}"
    )

def main() -> None:
    print("=== RUNTIME EDGE FAILURE ANALYSIS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("symbols=BRN6@RTSX,BRM6@RTSX,NGN6@RTSX")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOLS,))
            rows = [dict(r) for r in cur.fetchall()]

    by_root: dict[str, list[float]] = {}
    by_symbol: dict[str, list[float]] = {}
    by_hour: dict[tuple[str, int], list[float]] = {}
    by_weekday: dict[tuple[str, int], list[float]] = {}
    by_month: dict[tuple[str, str], list[float]] = {}

    for r in rows:
        symbol = r["symbol"]
        pnl = float(r["net_pnl"] or 0)
        ts = r["ts"]
        if ts is None:
            continue

        ts_msk = ts.astimezone(MSK)
        rt = root(symbol)

        by_root.setdefault(rt, []).append(pnl)
        by_symbol.setdefault(symbol, []).append(pnl)
        by_hour.setdefault((rt, ts_msk.hour), []).append(pnl)
        by_weekday.setdefault((rt, ts_msk.weekday()), []).append(pnl)
        by_month.setdefault((rt, ts_msk.strftime("%Y-%m")), []).append(pnl)

    print("ROOT_ROWS")
    for k in sorted(by_root):
        print_row("ROOT", f"root={k}", by_root[k])

    print()
    print("CONTRACT_ROWS")
    for k in sorted(by_symbol):
        print_row("CONTRACT", f"symbol={k}", by_symbol[k])

    print()
    print("HOUR_ROWS")
    for (rt, hour), values in sorted(by_hour.items()):
        print_row("HOUR", f"root={rt} hour_msk={hour}", values)

    print()
    print("WEEKDAY_ROWS")
    for (rt, weekday), values in sorted(by_weekday.items()):
        print_row("WEEKDAY", f"root={rt} weekday={weekday}", values)

    print()
    print("MONTH_ROWS")
    for (rt, month), values in sorted(by_month.items()):
        print_row("MONTH", f"root={rt} month={month}", values)

    print()
    print("FAILURE_SUMMARY")

    for rt, values in sorted(by_root.items()):
        root_m = metrics(values)
        bad_contracts = []
        for sym, sv in sorted(by_symbol.items()):
            if root(sym) == rt and status(metrics(sv)) == "FAILURE":
                bad_contracts.append(sym)

        print(
            "FAILURE_ROW "
            f"root={rt} "
            f"root_status={status(root_m)} "
            f"root_net_pnl={root_m['net_pnl']} "
            f"root_pf={root_m['profit_factor']} "
            f"bad_contracts={','.join(bad_contracts) if bad_contracts else 'NONE'}"
        )

    print()
    print("VERDICT=RUNTIME_EDGE_FAILURE_ANALYSIS_RECORDED")
    print("RUNTIME_EDGE_FAILURE_ANALYSIS_V1_OK")

if __name__ == "__main__":
    main()
