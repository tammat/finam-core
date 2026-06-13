#!/usr/bin/env python3
from __future__ import annotations

import os
from collections import defaultdict

import psycopg2
import psycopg2.extras

SYMBOL = "LKOH@MISX"
SOURCE_STRATEGY = "lkoh_shadow_signal_research_v1"
EXIT_BARS = 10
MIN_TRADES_PER_DAY = 10

SQL = """
WITH signals AS (
    SELECT
        signal_ts,
        DATE(signal_ts AT TIME ZONE 'Europe/Moscow') AS signal_day,
        side,
        entry_price::numeric AS entry_price,
        ROW_NUMBER() OVER (ORDER BY signal_ts) AS rn
    FROM lkoh_shadow_signals
    WHERE symbol=%s
      AND strategy=%s
      AND timeframe='M5'
      AND side='SELL'
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
            ELSE s.entry_price - e.entry_price
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
    winrate = round(len(wins) / trades * 100, 2) if trades else None
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    pf = round(gross_profit / gross_loss, 4) if gross_loss else None

    return {
        "trades": trades,
        "wins": len(wins),
        "losses": len(losses),
        "winrate": winrate,
        "net_pnl": net,
        "expectancy": expectancy,
        "profit_factor": pf,
    }

def classify_day(metrics: dict) -> str:
    trades = int(metrics["trades"])
    expectancy = metrics["expectancy"]
    pf = metrics["profit_factor"]

    if trades < MIN_TRADES_PER_DAY:
        return "NO_DATA"

    if expectancy is not None and expectancy > 0 and (pf or 0) >= 1.20:
        return "STRONG"

    if expectancy is not None and expectancy > 0:
        return "WEAK"

    return "NEGATIVE"

def main() -> int:
    print("=== LKOH SELL ONLY STABILITY AUDIT V1 ===")
    print("mode=stability_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"source_strategy={SOURCE_STRATEGY}")
    print(f"exit_bars={EXIT_BARS}")
    print()

    grouped: dict[str, list[float]] = defaultdict(list)

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, SOURCE_STRATEGY, EXIT_BARS))
            rows = cur.fetchall()

    for row in rows:
        grouped[str(row["signal_day"])].append(float(row["pnl"]))

    days_total = 0
    days_effective = 0
    days_positive = 0
    days_negative = 0
    days_strong = 0
    days_weak = 0
    days_no_data = 0

    all_pnls: list[float] = []
    positive_day_pnls: list[float] = []

    print("AUDIT_DAY_ROWS")

    for day in sorted(grouped.keys()):
        pnls = grouped[day]
        metrics = calc_metrics(pnls)
        status = classify_day(metrics)

        days_total += 1
        all_pnls.extend(pnls)

        if status == "NO_DATA":
            days_no_data += 1
        else:
            days_effective += 1

        if metrics["net_pnl"] > 0:
            days_positive += 1
            positive_day_pnls.append(float(metrics["net_pnl"]))
        elif metrics["net_pnl"] < 0:
            days_negative += 1

        if status == "STRONG":
            days_strong += 1
        elif status == "WEAK":
            days_weak += 1

        print(
            "AUDIT_DAY_ROW "
            f"date={day} "
            f"trades={metrics['trades']} "
            f"wins={metrics['wins']} "
            f"losses={metrics['losses']} "
            f"winrate={metrics['winrate']} "
            f"net_pnl={metrics['net_pnl']} "
            f"expectancy={metrics['expectancy']} "
            f"profit_factor={metrics['profit_factor']} "
            f"status={status}"
        )

    total = calc_metrics(all_pnls)

    stability_ratio = round(days_strong / max(days_effective, 1), 4)
    total_positive_pnl = sum(positive_day_pnls)
    max_positive_day_pnl = max(positive_day_pnls) if positive_day_pnls else 0.0
    profit_concentration_ratio = (
        round(max_positive_day_pnl / total_positive_pnl, 4)
        if total_positive_pnl > 0
        else None
    )

    if (
        stability_ratio >= 0.60
        and profit_concentration_ratio is not None
        and profit_concentration_ratio <= 0.30
    ):
        verdict = "LKOH_SELL_ONLY_READY_FOR_RUNTIME_REVIEW"
    elif stability_ratio >= 0.40:
        verdict = "LKOH_SELL_ONLY_SHADOW_VALIDATION"
    else:
        verdict = "LKOH_SELL_ONLY_REJECT"

    print()
    print(
        "AUDIT_SUMMARY_ROW "
        f"days_total={days_total} "
        f"days_effective={days_effective} "
        f"days_positive={days_positive} "
        f"days_negative={days_negative} "
        f"days_strong={days_strong} "
        f"days_weak={days_weak} "
        f"days_no_data={days_no_data} "
        f"net_pnl={total['net_pnl']} "
        f"expectancy={total['expectancy']} "
        f"profit_factor={total['profit_factor']} "
        f"stability_ratio={stability_ratio} "
        f"profit_concentration_ratio={profit_concentration_ratio}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={verdict}")
    print("LKOH_SELL_ONLY_STABILITY_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
