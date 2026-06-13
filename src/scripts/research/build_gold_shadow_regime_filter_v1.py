#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"
STRATEGY = "gold_short_only_shadow_v1"

SQL = """
WITH raw AS (
    SELECT
        s.signal_ts,
        s.signal_ts AT TIME ZONE 'Europe/Moscow' AS signal_ts_msk,
        DATE(s.signal_ts AT TIME ZONE 'Europe/Moscow') AS signal_day,
        s.side,
        s.entry_price::numeric AS entry_price,
        LEAD(s.entry_price::numeric, 10) OVER (
            PARTITION BY s.symbol, s.timeframe, s.strategy
            ORDER BY s.signal_ts
        ) AS exit_price
    FROM runtime_shadow_gold_signals s
    WHERE s.symbol=%s
      AND s.strategy=%s
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
),
day_regime AS (
    SELECT
        DATE(ts AT TIME ZONE 'Europe/Moscow') AS signal_day,
        MIN(close)::numeric AS min_close,
        MAX(close)::numeric AS max_close,
        (ARRAY_AGG(open ORDER BY ts))[1]::numeric AS first_open,
        (ARRAY_AGG(close ORDER BY ts DESC))[1]::numeric AS last_close,
        ROUND(((ARRAY_AGG(close ORDER BY ts DESC))[1]::numeric - (ARRAY_AGG(open ORDER BY ts))[1]::numeric), 6) AS day_move,
        ROUND((MAX(close)::numeric - MIN(close)::numeric), 6) AS day_range
    FROM market_bars
    WHERE symbol=%s
      AND timeframe='M5'
    GROUP BY DATE(ts AT TIME ZONE 'Europe/Moscow')
),
joined AS (
    SELECT
        s.*,
        d.first_open,
        d.last_close,
        d.day_move,
        d.day_range,
        CASE
            WHEN s.side='SELL'
             AND d.day_move > 0
             AND d.day_range >= 100
             AND s.entry_price < d.last_close
            THEN true
            ELSE false
        END AS would_block
    FROM scored s
    LEFT JOIN day_regime d ON d.signal_day = s.signal_day
)
SELECT *
FROM joined
WHERE pnl IS NOT NULL
ORDER BY signal_ts;
"""

def main() -> int:
    print("=== GOLD SHADOW REGIME FILTER V1 ===")
    print("mode=research_filter")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY, SYMBOL))
            rows = cur.fetchall()

    total = len(rows)
    blocked = [r for r in rows if r["would_block"]]
    allowed = [r for r in rows if not r["would_block"]]

    total_pnl = sum(float(r["pnl"] or 0) for r in rows)
    blocked_pnl = sum(float(r["pnl"] or 0) for r in blocked)
    allowed_pnl = sum(float(r["pnl"] or 0) for r in allowed)

    print("FILTER_ROWS")
    for r in rows:
        if r["would_block"]:
            print(
                "FILTER_ROW "
                f"signal_ts={r['signal_ts']} "
                f"signal_ts_msk={r['signal_ts_msk']} "
                f"side={r['side']} "
                f"entry={r['entry_price']} "
                f"exit={r['exit_price']} "
                f"pnl={r['pnl']} "
                f"day_move={r['day_move']} "
                f"day_range={r['day_range']} "
                "action=BLOCK "
                "reason=up_impulse_sell_block"
            )

    print()
    print(
        "SUMMARY_ROW "
        f"total_trades={total} "
        f"blocked_trades={len(blocked)} "
        f"allowed_trades={len(allowed)} "
        f"total_pnl={round(total_pnl, 6)} "
        f"blocked_pnl={round(blocked_pnl, 6)} "
        f"allowed_pnl={round(allowed_pnl, 6)} "
        f"pnl_after_filter={round(allowed_pnl, 6)}"
    )

    verdict = "GOLD_REGIME_FILTER_USEFUL" if blocked_pnl < 0 and allowed_pnl > 0 else "GOLD_REGIME_FILTER_NEEDS_REVIEW"

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={verdict}")
    print("GOLD_SHADOW_REGIME_FILTER_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
