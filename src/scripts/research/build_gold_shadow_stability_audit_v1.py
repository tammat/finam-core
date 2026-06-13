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
),
daily AS (
    SELECT
        signal_day,
        COUNT(*) AS signals,
        COUNT(*) FILTER (WHERE pnl IS NOT NULL) AS trades,
        COUNT(*) FILTER (WHERE pnl > 0) AS wins,
        COUNT(*) FILTER (WHERE pnl < 0) AS losses,
        ROUND(COALESCE(SUM(pnl), 0)::numeric, 6) AS net_pnl,
        ROUND(COALESCE(AVG(pnl), 0)::numeric, 6) AS expectancy,
        ROUND(CASE
            WHEN COUNT(*) FILTER (WHERE pnl IS NOT NULL) > 0
            THEN COUNT(*) FILTER (WHERE pnl > 0)::numeric
                 / COUNT(*) FILTER (WHERE pnl IS NOT NULL)::numeric
                 * 100
            ELSE NULL
        END, 2) AS winrate,
        ROUND((
            SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END)
            / NULLIF(ABS(SUM(CASE WHEN pnl < 0 THEN pnl ELSE 0 END)), 0)
        )::numeric, 4) AS profit_factor
    FROM scored
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
    if pf is not None and 0.8 <= pf < 1.0:
        return "NEUTRAL"
    return "WEAK"

def main() -> int:
    print("=== GOLD SHADOW STABILITY AUDIT V1 ===")
    print("mode=research_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY))
            rows = cur.fetchall()

    days_total = 0
    days_strong = 0
    days_healthy = 0
    days_weak = 0
    days_negative = 0
    days_no_data = 0

    total_signals = 0
    total_trades = 0
    total_net_pnl = 0.0

    print("DAY_ROWS")

    for row in rows:
        trades = int(row["trades"] or 0)
        signals = int(row["signals"] or 0)
        expectancy = float(row["expectancy"] or 0)
        net_pnl = float(row["net_pnl"] or 0)
        status = classify_day(trades, expectancy, row["profit_factor"])

        days_total += 1
        total_signals += signals
        total_trades += trades
        total_net_pnl += net_pnl

        if status == "STRONG":
            days_strong += 1
        elif status == "HEALTHY":
            days_healthy += 1
        elif status == "WEAK":
            days_weak += 1
        elif status == "NO_DATA":
            days_no_data += 1

        if net_pnl < 0:
            days_negative += 1

        print(
            "DAY_ROW "
            f"date={row['signal_day']} "
            f"signals={signals} "
            f"trades={trades} "
            f"wins={row['wins']} "
            f"losses={row['losses']} "
            f"winrate={row['winrate']} "
            f"expectancy={row['expectancy']} "
            f"profit_factor={row['profit_factor']} "
            f"net_pnl={row['net_pnl']} "
            f"status={status}"
        )

    effective_days = max(days_total - days_no_data, 1)
    stable_days = days_strong + days_healthy
    stability_ratio = round(stable_days / effective_days, 4)
    negative_ratio = round(days_negative / max(days_total, 1), 4)

    if stability_ratio >= 0.70 and negative_ratio <= 0.20:
        verdict = "GOLD_STABILITY_STRONG"
    else:
        verdict = "GOLD_STABILITY_UNSTABLE"

    print()
    print(
        "SUMMARY_ROW "
        f"days_total={days_total} "
        f"days_effective={effective_days} "
        f"days_strong={days_strong} "
        f"days_healthy={days_healthy} "
        f"days_weak={days_weak} "
        f"days_no_data={days_no_data} "
        f"days_negative={days_negative} "
        f"stability_ratio={stability_ratio} "
        f"negative_ratio={negative_ratio} "
        f"total_signals={total_signals} "
        f"total_trades={total_trades} "
        f"total_net_pnl={round(total_net_pnl, 6)}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={verdict}")
    print("GOLD_SHADOW_STABILITY_AUDIT_V1_OK")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
