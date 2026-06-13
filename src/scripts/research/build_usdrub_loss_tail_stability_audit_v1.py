#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict

import psycopg2
import psycopg2.extras

SYMBOL = "USDRUBF@RTSX"
STRATEGY = "usdrub_shadow_signal_research_v1"
EXIT_BARS = 10
LOSS_CAP = -2.0
MIN_TRADES_PER_DAY = 20

SQL = """
WITH signals AS (
    SELECT
        signal_ts,
        DATE(signal_ts AT TIME ZONE 'Europe/Moscow') AS signal_day,
        side,
        entry_price::numeric AS entry_price,
        ROW_NUMBER() OVER (ORDER BY signal_ts) AS rn
    FROM usdrub_shadow_signals
    WHERE symbol=%s
      AND strategy=%s
      AND timeframe='M5'
),
scored AS (
    SELECT
        s.signal_day,
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
WHERE pnl IS NOT NULL
ORDER BY signal_day, signal_ts;
"""

def calc_metrics(pnls: list[float]) -> dict:
    wins = [x for x in pnls if x > 0]
    losses = [x for x in pnls if x < 0]
    trades = len(pnls)
    net = round(sum(pnls), 6)
    expectancy = round(net / trades, 6) if trades else None
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = round(gross_profit / gross_loss, 4) if gross_loss else None

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "net_pnl": net,
        "expectancy": expectancy,
        "profit_factor": pf,
    }

def classify_day(trades: int, raw: dict, filtered: dict) -> str:
    if trades < MIN_TRADES_PER_DAY:
        return "NO_DATA"

    raw_net = float(raw["net_pnl"])
    filtered_net = float(filtered["net_pnl"])
    improvement = filtered_net - raw_net

    raw_pf = float(raw["profit_factor"] or 0)
    filtered_pf = float(filtered["profit_factor"] or 0)

    if improvement <= 0:
        return "NEGATIVE"

    if abs(raw_net) > 0 and improvement / abs(raw_net) < 0.10:
        return "WEAK"

    if filtered_pf >= raw_pf:
        return "STRONG"

    return "WEAK"

def main() -> int:
    print("=== USDRUB LOSS TAIL STABILITY AUDIT V1 ===")
    print("mode=stability_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"exit_bars={EXIT_BARS}")
    print(f"loss_cap={LOSS_CAP}")
    print()

    grouped: dict[str, list[float]] = defaultdict(list)

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY, EXIT_BARS))
            rows = cur.fetchall()

    for row in rows:
        grouped[str(row["signal_day"])].append(float(row["pnl"]))

    days_total = 0
    days_effective = 0
    days_improved = 0
    days_weak = 0
    days_negative = 0
    days_no_data = 0

    all_raw: list[float] = []
    all_filtered: list[float] = []

    print("AUDIT_DAY_ROWS")

    for day in sorted(grouped.keys()):
        raw_pnls = grouped[day]
        filtered_pnls = [max(x, LOSS_CAP) for x in raw_pnls]
        tail_trades = sum(1 for x in raw_pnls if x < LOSS_CAP)

        raw = calc_metrics(raw_pnls)
        filtered = calc_metrics(filtered_pnls)
        status = classify_day(len(raw_pnls), raw, filtered)

        improvement = round(float(filtered["net_pnl"]) - float(raw["net_pnl"]), 6)

        days_total += 1
        all_raw.extend(raw_pnls)
        all_filtered.extend(filtered_pnls)

        if status == "NO_DATA":
            days_no_data += 1
        else:
            days_effective += 1

        if status == "STRONG":
            days_improved += 1
        elif status == "WEAK":
            days_weak += 1
        elif status == "NEGATIVE":
            days_negative += 1

        print(
            "AUDIT_DAY_ROW "
            f"date={day} "
            f"trades={len(raw_pnls)} "
            f"tail_trades={tail_trades} "
            f"raw_net_pnl={raw['net_pnl']} "
            f"filtered_net_pnl={filtered['net_pnl']} "
            f"raw_expectancy={raw['expectancy']} "
            f"filtered_expectancy={filtered['expectancy']} "
            f"raw_pf={raw['profit_factor']} "
            f"filtered_pf={filtered['profit_factor']} "
            f"pnl_improvement={improvement} "
            f"status={status}"
        )

    raw_total = calc_metrics(all_raw)
    filtered_total = calc_metrics(all_filtered)

    stability_ratio = round(days_improved / max(days_effective, 1), 4)
    negative_ratio = round(days_negative / max(days_effective, 1), 4)

    raw_pf = float(raw_total["profit_factor"] or 0)
    filtered_pf = float(filtered_total["profit_factor"] or 0)

    if (
        stability_ratio >= 0.70
        and negative_ratio <= 0.20
        and float(filtered_total["net_pnl"]) > float(raw_total["net_pnl"])
        and filtered_pf > raw_pf
    ):
        verdict = "USDRUB_LOSS_TAIL_STABLE"
    else:
        verdict = "USDRUB_LOSS_TAIL_UNSTABLE"

    print()
    print(
        "AUDIT_SUMMARY_ROW "
        f"days_total={days_total} "
        f"days_effective={days_effective} "
        f"days_improved={days_improved} "
        f"days_weak={days_weak} "
        f"days_negative={days_negative} "
        f"days_no_data={days_no_data} "
        f"raw_pnl={raw_total['net_pnl']} "
        f"filtered_pnl={filtered_total['net_pnl']} "
        f"raw_pf={raw_total['profit_factor']} "
        f"filtered_pf={filtered_total['profit_factor']} "
        f"stability_ratio={stability_ratio} "
        f"negative_ratio={negative_ratio}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={verdict}")
    print("USDRUB_LOSS_TAIL_STABILITY_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
