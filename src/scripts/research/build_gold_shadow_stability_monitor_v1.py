#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"
STRATEGY = "gold_short_only_shadow_v1"

DDL = """
CREATE TABLE IF NOT EXISTS gold_shadow_stability_monitor (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    strategy text NOT NULL,
    stability_ratio numeric,
    negative_ratio numeric,
    days_total integer,
    days_effective integer,
    days_stable integer,
    days_weak integer,
    days_negative integer,
    total_signals integer,
    total_trades integer,
    filtered_pnl numeric,
    verdict text NOT NULL,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_gold_shadow_stability_monitor_symbol_created
ON gold_shadow_stability_monitor(symbol, created_at DESC);
"""

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
        ROUND(COALESCE(SUM(pnl) FILTER (WHERE NOT would_block), 0)::numeric, 6) AS filtered_net_pnl,
        COUNT(*) FILTER (WHERE NOT would_block AND pnl > 0) AS filtered_wins,
        COUNT(*) FILTER (WHERE NOT would_block AND pnl < 0) AS filtered_losses,
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

INSERT = """
INSERT INTO gold_shadow_stability_monitor (
    symbol,
    strategy,
    stability_ratio,
    negative_ratio,
    days_total,
    days_effective,
    days_stable,
    days_weak,
    days_negative,
    total_signals,
    total_trades,
    filtered_pnl,
    verdict,
    runtime_allowed,
    execution_enabled,
    raw_json
)
VALUES (
    %(symbol)s,
    %(strategy)s,
    %(stability_ratio)s,
    %(negative_ratio)s,
    %(days_total)s,
    %(days_effective)s,
    %(days_stable)s,
    %(days_weak)s,
    %(days_negative)s,
    %(total_signals)s,
    %(total_trades)s,
    %(filtered_pnl)s,
    %(verdict)s,
    false,
    false,
    %(raw_json)s
);
"""

def to_jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value

def classify_day(allowed_trades: int, expectancy: float, pf) -> str:
    pf_float = float(pf) if pf is not None else None

    if allowed_trades < 5:
        return "NO_DATA"
    if expectancy > 0 and pf_float is None:
        return "STRONG_NO_LOSSES"
    if expectancy > 0 and pf_float is not None and pf_float >= 1.5:
        return "STRONG"
    if expectancy > 0 and pf_float is not None and pf_float >= 1.0:
        return "HEALTHY"
    return "WEAK"

def main() -> int:
    print("=== GOLD SHADOW STABILITY MONITOR V1 ===")
    print("mode=stability_monitor")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL, (SYMBOL, STRATEGY, SYMBOL))
            rows = cur.fetchall()

            days_total = 0
            days_effective = 0
            days_stable = 0
            days_weak = 0
            days_negative = 0
            total_trades = 0
            filtered_pnl = 0.0

            day_payload = []

            print("MONITOR_DAY_ROWS")

            for row in rows:
                days_total += 1
                allowed_trades = int(row["allowed_trades"] or 0)
                expectancy = float(row["filtered_expectancy"] or 0)
                net_pnl = float(row["filtered_net_pnl"] or 0)
                status = classify_day(allowed_trades, expectancy, row["filtered_profit_factor"])

                total_trades += allowed_trades
                filtered_pnl += net_pnl

                if status != "NO_DATA":
                    days_effective += 1

                if status in ("STRONG", "HEALTHY", "STRONG_NO_LOSSES"):
                    days_stable += 1

                if status == "WEAK":
                    days_weak += 1

                if net_pnl < 0:
                    days_negative += 1

                payload_row = {k: to_jsonable(v) for k, v in dict(row).items()}
                payload_row["status"] = status
                day_payload.append(payload_row)

                print(
                    "MONITOR_DAY_ROW "
                    f"date={row['signal_day']} "
                    f"allowed_trades={allowed_trades} "
                    f"filtered_net_pnl={row['filtered_net_pnl']} "
                    f"filtered_expectancy={row['filtered_expectancy']} "
                    f"filtered_profit_factor={row['filtered_profit_factor']} "
                    f"status={status}"
                )

            stability_ratio = round(days_stable / max(days_effective, 1), 4)
            negative_ratio = round(days_negative / max(days_total, 1), 4)

            if days_effective >= 3 and stability_ratio >= 0.70 and negative_ratio <= 0.20 and filtered_pnl > 0:
                verdict = "GOLD_STABILITY_MONITOR_READY_FOR_REVIEW"
            else:
                verdict = "GOLD_STABILITY_MONITOR_CONTINUE_WATCH"

            payload = {
                "symbol": SYMBOL,
                "strategy": STRATEGY,
                "days_total": days_total,
                "days_effective": days_effective,
                "days_stable": days_stable,
                "days_weak": days_weak,
                "days_negative": days_negative,
                "stability_ratio": stability_ratio,
                "negative_ratio": negative_ratio,
                "total_trades": total_trades,
                "filtered_pnl": round(filtered_pnl, 6),
                "verdict": verdict,
                "runtime_allowed": False,
                "execution_enabled": False,
                "days": day_payload,
            }

            cur.execute(
                INSERT,
                {
                    "symbol": SYMBOL,
                    "strategy": STRATEGY,
                    "stability_ratio": stability_ratio,
                    "negative_ratio": negative_ratio,
                    "days_total": days_total,
                    "days_effective": days_effective,
                    "days_stable": days_stable,
                    "days_weak": days_weak,
                    "days_negative": days_negative,
                    "total_signals": 0,
                    "total_trades": total_trades,
                    "filtered_pnl": round(filtered_pnl, 6),
                    "verdict": verdict,
                    "raw_json": json.dumps(payload, ensure_ascii=False),
                },
            )

        conn.commit()

    print()
    print(
        "MONITOR_SUMMARY_ROW "
        f"days_total={days_total} "
        f"days_effective={days_effective} "
        f"days_stable={days_stable} "
        f"days_weak={days_weak} "
        f"days_negative={days_negative} "
        f"stability_ratio={stability_ratio} "
        f"negative_ratio={negative_ratio} "
        f"total_trades={total_trades} "
        f"filtered_pnl={round(filtered_pnl, 6)}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={verdict}")
    print("GOLD_SHADOW_STABILITY_MONITOR_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
