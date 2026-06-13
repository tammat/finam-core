#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"
STRATEGY = "gold_short_only_shadow_v1"
FAILURE_DAY = "2026-06-11"

SQL = """
WITH raw AS (
    SELECT
        symbol,
        timeframe,
        strategy,
        signal_ts,
        signal_ts AT TIME ZONE 'Europe/Moscow' AS signal_ts_msk,
        side,
        entry_price::numeric AS entry_price,
        LEAD(signal_ts, 10) OVER (
            PARTITION BY symbol, timeframe, strategy
            ORDER BY signal_ts
        ) AS exit_ts,
        LEAD(entry_price::numeric, 10) OVER (
            PARTITION BY symbol, timeframe, strategy
            ORDER BY signal_ts
        ) AS exit_price
    FROM runtime_shadow_gold_signals
    WHERE symbol=%s
      AND strategy=%s
),
scored AS (
    SELECT
        *,
        DATE(signal_ts AT TIME ZONE 'Europe/Moscow') AS signal_day,
        CASE
            WHEN exit_price IS NULL THEN NULL
            WHEN side='SELL' THEN entry_price - exit_price
            ELSE exit_price - entry_price
        END AS pnl
    FROM raw
)
SELECT
    signal_ts,
    signal_ts_msk,
    exit_ts,
    side,
    entry_price,
    exit_price,
    pnl
FROM scored
WHERE signal_day = %s::date
ORDER BY signal_ts;
"""

BAR_SQL = """
SELECT
    COUNT(*) AS bars,
    MIN(ts) AS first_bar_ts,
    MAX(ts) AS last_bar_ts,
    MIN(low) AS low,
    MAX(high) AS high,
    MIN(close) AS min_close,
    MAX(close) AS max_close,
    ROUND((MAX(close) - MIN(close))::numeric, 6) AS close_range
FROM market_bars
WHERE symbol=%s
  AND timeframe='M5'
  AND DATE(ts AT TIME ZONE 'Europe/Moscow') = %s::date;
"""

def classify_failure(rows: list[dict]) -> str:
    losses = [r for r in rows if r["pnl"] is not None and float(r["pnl"]) < 0]
    if len(rows) > 0 and len(losses) == len(rows):
        return "ALL_TRADES_LOST"
    if losses:
        return "PARTIAL_FAILURE"
    return "NO_FAILURE"

def main() -> int:
    print("=== GOLD SHADOW FAILURE DAY ANALYSIS V1 ===")
    print("mode=research_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"failure_day={FAILURE_DAY}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY, FAILURE_DAY))
            rows = cur.fetchall()

            cur.execute(BAR_SQL, (SYMBOL, FAILURE_DAY))
            bars = cur.fetchone()

    print("FAILURE_TRADE_ROWS")

    total_pnl = 0.0
    losses = 0
    wins = 0

    for i, row in enumerate(rows, start=1):
        pnl = float(row["pnl"]) if row["pnl"] is not None else None
        if pnl is not None:
            total_pnl += pnl
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1

        print(
            "FAILURE_TRADE_ROW "
            f"n={i} "
            f"signal_ts={row['signal_ts']} "
            f"signal_ts_msk={row['signal_ts_msk']} "
            f"exit_ts={row['exit_ts']} "
            f"side={row['side']} "
            f"entry_price={row['entry_price']} "
            f"exit_price={row['exit_price']} "
            f"pnl={row['pnl']}"
        )

    classification = classify_failure(rows)

    print()
    print(
        "MARKET_DAY_ROW "
        f"bars={bars['bars']} "
        f"first_bar_ts={bars['first_bar_ts']} "
        f"last_bar_ts={bars['last_bar_ts']} "
        f"low={bars['low']} "
        f"high={bars['high']} "
        f"min_close={bars['min_close']} "
        f"max_close={bars['max_close']} "
        f"close_range={bars['close_range']}"
    )

    print()
    print(
        "FAILURE_SUMMARY_ROW "
        f"trades={len(rows)} "
        f"wins={wins} "
        f"losses={losses} "
        f"net_pnl={round(total_pnl, 6)} "
        f"classification={classification}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=GOLD_FAILURE_DAY_CONFIRMED")
    print("GOLD_SHADOW_FAILURE_DAY_ANALYSIS_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
