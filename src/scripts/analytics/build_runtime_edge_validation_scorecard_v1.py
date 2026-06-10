#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SQL_CLOSED = """
SELECT
    symbol,
    COUNT(*) AS trades,
    ROUND(COALESCE(SUM(net_pnl),0)::numeric,6) AS net_pnl,
    ROUND(COALESCE(AVG(net_pnl),0)::numeric,6) AS expectancy,
    ROUND(
        100.0 * SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0),
        2
    ) AS winrate,
    ROUND(COALESCE(SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END),0)::numeric,6) AS gross_profit,
    ROUND(COALESCE(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)),0)::numeric,6) AS gross_loss,
    MAX(COALESCE(exit_ts, closed_at, created_at)) AS last_trade_ts
FROM closed_trades
WHERE symbol = ANY(%s)
GROUP BY symbol;
"""

SQL_GOLD_SHADOW = """
SELECT
    symbol,
    COUNT(*) AS shadow_signals,
    COUNT(DISTINCT signal_ts) AS distinct_shadow_signals,
    MAX(signal_ts) AS last_shadow_ts
FROM runtime_shadow_gold_signals
WHERE symbol = ANY(%s)
GROUP BY symbol;
"""

def pf(gp, gl):
    gp_f = float(gp or 0)
    gl_f = float(gl or 0)
    if gl_f <= 0:
        return None
    return round(gp_f / gl_f, 4)

def runtime_status(trades: int, expectancy: float, profit_factor, shadow_signals: int = 0) -> str:
    if trades >= 30 and expectancy > 0 and profit_factor is not None and profit_factor >= 1.2:
        return "KEEP"
    if trades >= 30 and expectancy <= 0:
        return "REJECT"
    if shadow_signals > 0 and trades == 0:
        return "ACCUMULATING"
    return "WATCH"

def main() -> None:
    print("=== RUNTIME EDGE VALIDATION SCORECARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    edge_defs = [
        {
            "name": "BR_RUNTIME",
            "symbols": ["BRN6@RTSX", "BRM6@RTSX"],
            "replay_expectancy": None,
            "replay_pf": None,
        },
        {
            "name": "NG_RUNTIME",
            "symbols": ["NGN6@RTSX"],
            "replay_expectancy": None,
            "replay_pf": None,
        },
        {
            "name": "USD_RUNTIME",
            "symbols": ["USDRUBF@RTSX"],
            "replay_expectancy": None,
            "replay_pf": None,
        },
        {
            "name": "GOLD_SHORT_ONLY",
            "symbols": ["GDU6@RTSX"],
            "replay_expectancy": 7.828671,
            "replay_pf": 2.947,
        },
    ]

    all_symbols = sorted({s for e in edge_defs for s in e["symbols"]})
    gold_symbols = ["GDU6@RTSX", "GDM6@RTSX"]

    closed_by_symbol = {}
    shadow_by_symbol = {}

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_CLOSED, (all_symbols,))
            for r in cur.fetchall():
                closed_by_symbol[r["symbol"]] = dict(r)

            try:
                cur.execute(SQL_GOLD_SHADOW, (gold_symbols,))
                for r in cur.fetchall():
                    shadow_by_symbol[r["symbol"]] = dict(r)
            except Exception:
                shadow_by_symbol = {}

    print("EDGE_ROWS")

    for edge in edge_defs:
        symbols = edge["symbols"]

        trades = 0
        net_pnl = 0.0
        gross_profit = 0.0
        gross_loss = 0.0
        last_trade_ts = None

        for symbol in symbols:
            row = closed_by_symbol.get(symbol)
            if not row:
                continue
            trades += int(row["trades"] or 0)
            net_pnl += float(row["net_pnl"] or 0)
            gross_profit += float(row["gross_profit"] or 0)
            gross_loss += float(row["gross_loss"] or 0)
            ts = row["last_trade_ts"]
            if ts is not None and (last_trade_ts is None or ts > last_trade_ts):
                last_trade_ts = ts

        expectancy = round(net_pnl / trades, 6) if trades else 0.0
        profit_factor = pf(gross_profit, gross_loss)

        shadow_signals = 0
        last_shadow_ts = None
        for symbol in symbols:
            srow = shadow_by_symbol.get(symbol)
            if not srow:
                continue
            shadow_signals += int(srow["distinct_shadow_signals"] or 0)
            ts = srow["last_shadow_ts"]
            if ts is not None and (last_shadow_ts is None or ts > last_shadow_ts):
                last_shadow_ts = ts

        status = runtime_status(trades, expectancy, profit_factor, shadow_signals)

        print(
            "EDGE_ROW "
            f"strategy={edge['name']} "
            f"symbols={','.join(symbols)} "
            f"replay_expectancy={edge['replay_expectancy']} "
            f"replay_pf={edge['replay_pf']} "
            f"shadow_signals={shadow_signals} "
            f"runtime_trades={trades} "
            f"runtime_net_pnl={round(net_pnl,6)} "
            f"runtime_expectancy={expectancy} "
            f"runtime_profit_factor={profit_factor} "
            f"last_trade_ts={last_trade_ts} "
            f"last_shadow_ts={last_shadow_ts} "
            f"status={status}"
        )

    print()
    print("VERDICT=RUNTIME_EDGE_VALIDATION_RECORDED")
    print("RUNTIME_EDGE_VALIDATION_SCORECARD_V1_OK")

if __name__ == "__main__":
    main()
