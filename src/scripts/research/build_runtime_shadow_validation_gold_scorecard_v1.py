#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = os.getenv("GOLD_SYMBOL", "GDU6@RTSX")
STRATEGY = "gold_short_only_shadow_v1"
TARGET_SIGNALS = 50

SQL = """
WITH signals AS (
    SELECT
        id,
        symbol,
        timeframe,
        signal_ts,
        side,
        entry_price::numeric AS entry_price,
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
        CASE
            WHEN exit_price IS NULL THEN NULL
            WHEN side='SELL' THEN entry_price - exit_price
            ELSE exit_price - entry_price
        END AS pnl
    FROM signals
)
SELECT
    COUNT(*) AS signals,
    COUNT(*) FILTER (WHERE pnl IS NOT NULL) AS closed_shadow_trades,
    COUNT(*) FILTER (WHERE pnl > 0) AS wins,
    COUNT(*) FILTER (WHERE pnl < 0) AS losses,
    ROUND(COALESCE(SUM(pnl),0)::numeric, 6) AS net_pnl,
    ROUND(COALESCE(AVG(pnl),0)::numeric, 6) AS expectancy,
    ROUND((
        SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)
        / NULLIF(ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0)
    )::numeric, 4) AS profit_factor,
    MIN(signal_ts) AS first_signal_ts,
    MAX(signal_ts) AS last_signal_ts
FROM scored;
"""

def main() -> None:
    print("=== RUNTIME SHADOW VALIDATION GOLD SCORECARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"target_signals={TARGET_SIGNALS}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY))
            row = cur.fetchone()

    signals = int(row["signals"] or 0)
    closed = int(row["closed_shadow_trades"] or 0)
    wins = int(row["wins"] or 0)
    losses = int(row["losses"] or 0)
    expectancy = float(row["expectancy"] or 0)
    pf = row["profit_factor"]
    pf_float = float(pf) if pf is not None else None

    if signals < TARGET_SIGNALS or closed < 30:
        decision = "WATCH_ONLY"
        reason = "insufficient_closed_shadow_sample"
    elif expectancy > 0 and pf_float is not None and pf_float >= 1.2:
        decision = "PROMOTE_CANDIDATE"
        reason = "positive_expectancy_and_pf"
    else:
        decision = "REJECT"
        reason = "negative_or_weak_shadow_edge"

    print(
        "SCORECARD_ROW "
        f"symbol={SYMBOL} "
        f"signals={signals} "
        f"closed_shadow_trades={closed} "
        f"wins={wins} "
        f"losses={losses} "
        f"net_pnl={row['net_pnl']} "
        f"expectancy={row['expectancy']} "
        f"profit_factor={row['profit_factor']} "
        f"first_signal_ts={row['first_signal_ts']} "
        f"last_signal_ts={row['last_signal_ts']} "
        f"decision={decision} "
        f"reason={reason}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT=GOLD_SCORECARD_{decision}")
    print("RUNTIME_SHADOW_VALIDATION_GOLD_SCORECARD_V1_OK")

if __name__ == "__main__":
    main()
