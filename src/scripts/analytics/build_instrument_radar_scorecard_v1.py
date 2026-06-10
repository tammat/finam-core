#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

CANDIDATES = [
    ("GOLD", "GDU6@RTSX"),
    ("BR", "BRN6@RTSX"),
    ("NG", "NGN6@RTSX"),
    ("USD", "USDRUBF@RTSX"),
    ("SBER", "SBER@MISX"),
    ("LKOH", "LKOH@MISX"),
    ("GAZP", "GAZP@MISX"),
    ("PLZL", "PLZL@MISX"),
]

SQL = """
WITH closed AS (
    SELECT
        symbol,
        COUNT(*) AS trades,
        COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
        COUNT(*) FILTER (WHERE net_pnl <= 0) AS losses,
        ROUND(COALESCE(SUM(net_pnl),0)::numeric,6) AS net_pnl,
        ROUND(COALESCE(AVG(net_pnl),0)::numeric,6) AS expectancy,
        ROUND(
            (
                SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
                /
                NULLIF(ABS(SUM(CASE WHEN net_pnl <= 0 THEN net_pnl ELSE 0 END)),0)
            )::numeric,
            4
        ) AS profit_factor,
        MAX(COALESCE(exit_ts, closed_at, created_at)) AS last_trade_ts
    FROM closed_trades
    WHERE trade_source='paper'
      AND source='closed_trade_engine_v1_1'
    GROUP BY symbol
),
bars AS (
    SELECT
        symbol,
        COUNT(*) AS bars,
        MAX(ts) AS last_bar_ts
    FROM market_bars
    GROUP BY symbol
),
gold_shadow AS (
    SELECT
        symbol,
        COUNT(*) AS shadow_signals,
        MAX(signal_ts) AS last_shadow_ts
    FROM runtime_shadow_gold_signals
    GROUP BY symbol
)
SELECT
    %(root)s AS root,
    %(symbol)s AS symbol,
    COALESCE(b.bars,0) AS bars,
    b.last_bar_ts,
    COALESCE(c.trades,0) AS trades,
    COALESCE(c.wins,0) AS wins,
    COALESCE(c.losses,0) AS losses,
    COALESCE(c.net_pnl,0) AS net_pnl,
    COALESCE(c.expectancy,0) AS expectancy,
    c.profit_factor,
    c.last_trade_ts,
    COALESCE(g.shadow_signals,0) AS shadow_signals,
    g.last_shadow_ts
FROM (SELECT 1) x
LEFT JOIN closed c ON c.symbol=%(symbol)s
LEFT JOIN bars b ON b.symbol=%(symbol)s
LEFT JOIN gold_shadow g ON g.symbol=%(symbol)s;
"""

def classify(row: dict) -> tuple[str, str]:
    trades = int(row["trades"] or 0)
    bars = int(row["bars"] or 0)
    shadow = int(row["shadow_signals"] or 0)
    expectancy = float(row["expectancy"] or 0)
    pf = row["profit_factor"]
    pfv = float(pf) if pf is not None else None

    if shadow >= 20 and trades == 0:
        return "SHADOW_ACCUMULATING", "shadow_signals_without_runtime_trades"

    if trades >= 30 and expectancy > 0 and pfv is not None and pfv >= 1.2:
        return "RESEARCH_CANDIDATE", "positive_closed_trade_stats"

    if trades >= 30 and expectancy <= 0:
        return "REJECT", "negative_closed_trade_expectancy"

    if bars >= 100 and trades < 30:
        return "WATCH", "bars_available_insufficient_trades"

    if bars == 0:
        return "NO_DATA", "no_market_bars"

    return "WATCH", "insufficient_evidence"

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== INSTRUMENT RADAR SCORECARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    rows = []

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for root, symbol in CANDIDATES:
                cur.execute(SQL, {"root": root, "symbol": symbol})
                row = cur.fetchone()
                action, reason = classify(row)
                row["action"] = action
                row["reason"] = reason
                rows.append(row)

    print("RADAR_ROWS")
    for r in rows:
        print(
            "RADAR_ROW "
            f"root={r['root']} "
            f"symbol={r['symbol']} "
            f"bars={r['bars']} "
            f"last_bar_ts={r['last_bar_ts']} "
            f"trades={r['trades']} "
            f"wins={r['wins']} "
            f"losses={r['losses']} "
            f"net_pnl={r['net_pnl']} "
            f"expectancy={r['expectancy']} "
            f"profit_factor={r['profit_factor']} "
            f"shadow_signals={r['shadow_signals']} "
            f"last_shadow_ts={r['last_shadow_ts']} "
            f"action={r['action']} "
            f"reason={r['reason']}"
        )

    counts = {}
    for r in rows:
        counts[r["action"]] = counts.get(r["action"], 0) + 1

    print()
    print(
        "SUMMARY_ROW "
        f"rows={len(rows)} "
        f"shadow_accumulating={counts.get('SHADOW_ACCUMULATING',0)} "
        f"research_candidate={counts.get('RESEARCH_CANDIDATE',0)} "
        f"watch={counts.get('WATCH',0)} "
        f"reject={counts.get('REJECT',0)} "
        f"no_data={counts.get('NO_DATA',0)}"
    )

    print("VERDICT=INSTRUMENT_RADAR_SCORECARD_RECORDED")
    print("INSTRUMENT_RADAR_SCORECARD_V1_OK")

if __name__ == "__main__":
    main()
