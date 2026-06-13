#!/usr/bin/env python3
from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

SYMBOL = "LKOH@MISX"
STRATEGY = "lkoh_shadow_signal_research_v1"
EXIT_BARS = 10

SQL = """
WITH signals AS (
    SELECT
        signal_ts,
        side,
        entry_price::numeric AS entry_price,
        ROW_NUMBER() OVER (ORDER BY signal_ts) AS rn
    FROM lkoh_shadow_signals
    WHERE symbol=%s
      AND strategy=%s
      AND timeframe='M5'
),
scored AS (
    SELECT
        s.signal_ts,
        s.side,
        s.entry_price,
        e.signal_ts AS exit_ts,
        e.entry_price AS exit_price,
        CASE
            WHEN e.entry_price IS NULL THEN NULL
            WHEN s.side='BUY' THEN e.entry_price - s.entry_price
            WHEN s.side='SELL' THEN s.entry_price - e.entry_price
            ELSE NULL
        END AS pnl
    FROM signals s
    LEFT JOIN signals e ON e.rn = s.rn + %s
)
SELECT *
FROM scored
WHERE pnl IS NOT NULL;
"""

def avg(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None

def main() -> int:
    print("=== LKOH SHADOW FAILURE ANALYSIS V1 ===")
    print("mode=failure_analysis")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"exit_bars={EXIT_BARS}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY, EXIT_BARS))
            rows = cur.fetchall()

    pnls = [float(r["pnl"]) for r in rows]
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]

    buy_rows = [r for r in rows if r["side"] == "BUY"]
    sell_rows = [r for r in rows if r["side"] == "SELL"]

    buy_pnls = [float(r["pnl"]) for r in buy_rows]
    sell_pnls = [float(r["pnl"]) for r in sell_rows]

    avg_win = avg(wins)
    avg_loss = avg(losses)
    largest_win = round(max(wins), 6) if wins else None
    largest_loss = round(min(losses), 6) if losses else None

    buy_expectancy = avg(buy_pnls)
    sell_expectancy = avg(sell_pnls)

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = round(gross_profit / gross_loss, 4) if gross_loss else None

    if avg_loss is not None and largest_loss is not None and abs(largest_loss) > abs(avg_loss) * 5:
        failure_mode = "LOSS_TAIL"
    elif buy_expectancy is not None and sell_expectancy is not None and buy_expectancy > 0 and sell_expectancy < 0:
        failure_mode = "SELL_SIDE_WEAK"
    elif buy_expectancy is not None and sell_expectancy is not None and sell_expectancy > 0 and buy_expectancy < 0:
        failure_mode = "BUY_SIDE_WEAK"
    elif buy_expectancy is not None and sell_expectancy is not None and buy_expectancy < 0 and sell_expectancy < 0:
        failure_mode = "NO_EDGE"
    else:
        failure_mode = "LOW_SIGNAL_QUALITY"

    print(
        "SUMMARY_ROW "
        f"closed_trades={len(rows)} "
        f"wins={len(wins)} "
        f"losses={len(losses)} "
        f"avg_win={avg_win} "
        f"avg_loss={avg_loss} "
        f"largest_win={largest_win} "
        f"largest_loss={largest_loss} "
        f"profit_factor={profit_factor} "
        f"buy_trades={len(buy_rows)} "
        f"buy_expectancy={buy_expectancy} "
        f"sell_trades={len(sell_rows)} "
        f"sell_expectancy={sell_expectancy} "
        f"failure_mode={failure_mode}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=LKOH_FAILURE_ANALYSIS_READY")
    print("LKOH_SHADOW_FAILURE_ANALYSIS_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
