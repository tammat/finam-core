#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"
STRATEGY = "gold_short_only_shadow_v1"
MIN_TRADES_PER_DAY = 5

SQL = """
WITH raw AS (
    SELECT
        s.symbol,
        s.timeframe,
        s.strategy,
        s.signal_ts,
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
        (ARRAY_AGG(open ORDER BY ts))[1]::numeric AS first_open,
        (ARRAY_AGG(close ORDER BY ts DESC))[1]::numeric AS last_close,
        ROUND(((ARRAY_AGG(close ORDER BY ts DESC))[1]::numeric - (ARRAY_AGG(open ORDER BY ts))[1]::numeric), 6) AS day_move,
        ROUND((MAX(close)::numeric - MIN(close)::numeric), 6) AS day_range
    FROM market_bars
    WHERE symbol=%s
      AND timeframe='M5'
    GROUP BY DATE(ts AT TIME ZONE 'Europe/Moscow')
),
filtered AS (
    SELECT
        s.*,
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
    WHERE s.pnl IS NOT NULL
),
daily AS (
    SELECT
        signal_day,
        COUNT(*) AS original_trades,
        COUNT(*) FILTER (WHERE would_block) AS blocked_trades,
        COUNT(*) FILTER (WHERE NOT would_block) AS allowed_trades,
        ROUND(COALESCE(SUM(pnl), 0)::numeric, 6) AS original_net_pnl,
        ROUND(COALESCE(SUM(pnl) FILTER (WHERE would_block), 0)::numeric, 6) AS blocked_pnl,
        ROUND(COALESCE(SUM(pnl) FILTER (WHERE NOT would_block), 0)::numeric, 6) AS filtered_net_pnl,
        COUNT(*) FILTER (WHERE NOT would_block AND pnl > 0) AS filtered_wins,
        COUNT(*) FILTER (WHERE NOT would_block AND pnl < 0) AS filtered_losses,
        ROUND(CASE
            WHEN COUNT(*) FILTER (WHERE NOT would_block) > 0
            THEN COUNT(*) FILTER (WHERE NOT would_block AND pnl > 0)::numeric
                 / COUNT(*) FILTER (WHERE NOT would_block)::numeric * 100
            ELSE NULL
        END, 2) AS filtered_winrate,
        ROUND(COALESCE(AVG(pnl) FILTER (WHERE NOT would_block), 0)::numeric, 6) AS filtered_expectancy,
        ROUND((
            SUM(CASE WHEN NOT would_block AND pnl > 0 THEN pnl ELSE 0 END)
            / NULLIF(ABS(SUM(CASE WHEN NOT would_block AND pnl < 0 THEN pnl ELSE 0 END)), 0)
        )::numeric, 4) AS filtered_profit_factor
    FROM filtered
    GROUP BY signal_day
)
SELECT *
FROM daily
ORDER BY signal_day;
"""

def classify_day(trades: int, expectancy: float, pf_raw) -> str:
    pf = float(pf_raw) if pf_raw is not None else None

    if trades < MIN_TRADES_PER_DAY:
        return "NO_DATA"
    if expectancy > 0 and pf is not None and pf >= 1.5:
        return "STRONG"
    if expectancy > 0 and pf is not None and pf >= 1.0:
        return "HEALTHY"
    if expectancy > 0 and pf is None:
        return "STRONG_NO_LOSSES"
    if pf is not None and 0.8 <= pf < 1.0:
        return "NEUTRAL"
    return "WEAK"

def main() -> int:
    print("=== GOLD SHADOW REGIME FILTER BACKTEST V1 ===")
    print("mode=research_backtest")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print("filter=up_impulse_sell_block")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY, SYMBOL))
            rows = cur.fetchall()

    days_total = 0
    days_effective = 0
    days_stable = 0
    days_weak = 0
    days_no_data = 0
    days_negative = 0

    total_original_pnl = 0.0
    total_blocked_pnl = 0.0
    total_filtered_pnl = 0.0
    total_original_trades = 0
    total_blocked_trades = 0
    total_allowed_trades = 0

    print("BACKTEST_DAY_ROWS")

    for row in rows:
        days_total += 1

        allowed_trades = int(row["allowed_trades"] or 0)
        filtered_expectancy = float(row["filtered_expectancy"] or 0)
        filtered_net_pnl = float(row["filtered_net_pnl"] or 0)
        status = classify_day(allowed_trades, filtered_expectancy, row["filtered_profit_factor"])

        total_original_pnl += float(row["original_net_pnl"] or 0)
        total_blocked_pnl += float(row["blocked_pnl"] or 0)
        total_filtered_pnl += filtered_net_pnl
        total_original_trades += int(row["original_trades"] or 0)
        total_blocked_trades += int(row["blocked_trades"] or 0)
        total_allowed_trades += allowed_trades

        if status == "NO_DATA":
            days_no_data += 1
        else:
            days_effective += 1

        if status in ("STRONG", "HEALTHY", "STRONG_NO_LOSSES"):
            days_stable += 1

        if status == "WEAK":
            days_weak += 1

        if filtered_net_pnl < 0:
            days_negative += 1

        print(
            "BACKTEST_DAY_ROW "
            f"date={row['signal_day']} "
            f"original_trades={row['original_trades']} "
            f"blocked_trades={row['blocked_trades']} "
            f"allowed_trades={row['allowed_trades']} "
            f"original_net_pnl={row['original_net_pnl']} "
            f"blocked_pnl={row['blocked_pnl']} "
            f"filtered_net_pnl={row['filtered_net_pnl']} "
            f"filtered_wins={row['filtered_wins']} "
            f"filtered_losses={row['filtered_losses']} "
            f"filtered_winrate={row['filtered_winrate']} "
            f"filtered_expectancy={row['filtered_expectancy']} "
            f"filtered_profit_factor={row['filtered_profit_factor']} "
            f"status={status}"
        )

    stability_ratio = round(days_stable / max(days_effective, 1), 4)
    negative_ratio = round(days_negative / max(days_total, 1), 4)

    if stability_ratio >= 0.70 and negative_ratio <= 0.20 and total_filtered_pnl > total_original_pnl:
        verdict = "GOLD_REGIME_FILTER_BACKTEST_STRONG"
    else:
        verdict = "GOLD_REGIME_FILTER_BACKTEST_NEEDS_MORE_DATA"

    print()
    print(
        "BACKTEST_SUMMARY_ROW "
        f"days_total={days_total} "
        f"days_effective={days_effective} "
        f"days_stable={days_stable} "
        f"days_weak={days_weak} "
        f"days_no_data={days_no_data} "
        f"days_negative={days_negative} "
        f"stability_ratio={stability_ratio} "
        f"negative_ratio={negative_ratio} "
        f"original_trades={total_original_trades} "
        f"blocked_trades={total_blocked_trades} "
        f"allowed_trades={total_allowed_trades} "
        f"original_pnl={round(total_original_pnl, 6)} "
        f"blocked_pnl={round(total_blocked_pnl, 6)} "
        f"filtered_pnl={round(total_filtered_pnl, 6)} "
        f"pnl_improvement={round(total_filtered_pnl - total_original_pnl, 6)}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={verdict}")
    print("GOLD_SHADOW_REGIME_FILTER_BACKTEST_V1_OK")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
