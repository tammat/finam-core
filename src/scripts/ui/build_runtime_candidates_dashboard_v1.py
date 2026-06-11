#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOLS = ["GDU6@RTSX", "USDRUBF@RTSX", "LKOH@MISX", "NGN6@RTSX", "BRN6@RTSX", "SBER@MISX", "PLZL@MISX", "GAZP@MISX"]

SQL = """
WITH src AS (
    SELECT unnest(%s::text[]) AS symbol
),
bars AS (
    SELECT symbol, COUNT(*) AS bars, MAX(ts) AS last_bar_ts
    FROM market_bars
    WHERE symbol = ANY(%s)
    GROUP BY symbol
),
closed AS (
    SELECT
        symbol,
        COUNT(*) AS trades,
        COUNT(*) FILTER (WHERE net_pnl > 0) AS wins,
        ROUND(COALESCE(AVG(net_pnl),0)::numeric, 6) AS expectancy,
        ROUND((
            SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END)
            / NULLIF(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)), 0)
        )::numeric, 4) AS profit_factor
    FROM closed_trades
    WHERE symbol = ANY(%s)
    GROUP BY symbol
),
gold_shadow AS (
    WITH raw AS (
        SELECT
            symbol,
            timeframe,
            strategy,
            signal_ts,
            side,
            entry_price::numeric AS entry_price,
            LEAD(entry_price::numeric, 10) OVER (
                PARTITION BY symbol, timeframe, strategy
                ORDER BY signal_ts
            ) AS exit_price
        FROM runtime_shadow_gold_signals
        WHERE symbol='GDU6@RTSX'
          AND strategy='gold_short_only_shadow_v1'
    ),
    scored AS (
        SELECT
            *,
            CASE
                WHEN exit_price IS NULL THEN NULL
                WHEN side='SELL' THEN entry_price - exit_price
                ELSE exit_price - entry_price
            END AS pnl
        FROM raw
    )
    SELECT
        symbol,
        COUNT(*) AS shadow_signals,
        COUNT(*) FILTER (WHERE pnl IS NOT NULL) AS shadow_trades,
        COUNT(*) FILTER (WHERE pnl > 0) AS shadow_wins,
        ROUND(CASE
            WHEN COUNT(*) FILTER (WHERE pnl IS NOT NULL) > 0
            THEN COUNT(*) FILTER (WHERE pnl > 0)::numeric
                 / COUNT(*) FILTER (WHERE pnl IS NOT NULL)::numeric * 100
            ELSE NULL
        END, 2) AS shadow_winrate,
        ROUND(COALESCE(AVG(pnl),0)::numeric, 6) AS shadow_expectancy,
        ROUND((
            SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)
            / NULLIF(ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0)
        )::numeric, 4) AS shadow_profit_factor
    FROM scored
    GROUP BY symbol
)
SELECT
    src.symbol,
    COALESCE(b.bars, 0) AS bars,
    b.last_bar_ts,
    COALESCE(c.trades, 0) AS trades,
    CASE
        WHEN COALESCE(c.trades, 0) > 0
        THEN ROUND((c.wins::numeric / c.trades::numeric * 100), 2)
        ELSE NULL
    END AS winrate,
    c.expectancy,
    c.profit_factor,
    gs.shadow_signals,
    gs.shadow_trades,
    gs.shadow_winrate,
    gs.shadow_expectancy,
    gs.shadow_profit_factor
FROM src
LEFT JOIN bars b ON b.symbol = src.symbol
LEFT JOIN closed c ON c.symbol = src.symbol
LEFT JOIN gold_shadow gs ON gs.symbol = src.symbol
ORDER BY src.symbol;
"""

def classify(row: dict) -> tuple[str, str]:
    symbol = row["symbol"]
    trades = int(row["trades"] or 0)
    bars = int(row["bars"] or 0)
    expectancy = float(row["expectancy"] or 0)
    pf = float(row["profit_factor"]) if row["profit_factor"] is not None else None
    shadow_signals = int(row["shadow_signals"] or 0)
    shadow_expectancy = float(row["shadow_expectancy"] or 0)

    if symbol == "GDU6@RTSX" and shadow_signals >= 50 and shadow_expectancy > 0:
        return "WATCH_RUNTIME_CANDIDATE", "gold_shadow_passed"
    if bars == 0:
        return "NO_DATA", "no_market_bars"
    if symbol in ("BRN6@RTSX", "NGN6@RTSX") and expectancy <= 0:
        return "REJECTED", "negative_expectancy"
    if trades > 0 and pf is not None and pf > 1:
        return "WATCH", "positive_closed_trade_statistics"
    return "RESEARCH", "needs_more_validation"

def main() -> int:
    print("=== UI RUNTIME CANDIDATES DASHBOARD V1 ===")
    print("mode=read_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOLS, SYMBOLS, SYMBOLS))
            rows = cur.fetchall()

    counts = {}
    print("CANDIDATE_ROWS")
    for row in rows:
        status, reason = classify(row)
        counts[status] = counts.get(status, 0) + 1
        print(
            "CANDIDATE_ROW "
            f"symbol={row['symbol']} "
            f"bars={row['bars']} "
            f"trades={row['trades']} "
            f"winrate={row['winrate']} "
            f"expectancy={row['expectancy']} "
            f"profit_factor={row['profit_factor']} "
            f"shadow_signals={row['shadow_signals']} "
            f"shadow_trades={row['shadow_trades']} "
            f"shadow_winrate={row['shadow_winrate']} "
            f"shadow_expectancy={row['shadow_expectancy']} "
            f"shadow_profit_factor={row['shadow_profit_factor']} "
            f"status={status} "
            f"reason={reason}"
        )

    print()
    print(
        "SUMMARY_ROW "
        f"promote_candidates={counts.get('WATCH_RUNTIME_CANDIDATE', 0)} "
        f"watch={counts.get('WATCH', 0)} "
        f"research={counts.get('RESEARCH', 0)} "
        f"rejected={counts.get('REJECTED', 0)} "
        f"no_data={counts.get('NO_DATA', 0)}"
    )
    print("VERDICT=UI_RUNTIME_CANDIDATES_DASHBOARD_READY")
    print("UI_RUNTIME_CANDIDATES_DASHBOARD_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
