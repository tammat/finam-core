#!/usr/bin/env python3
from __future__ import annotations

import math
import os
import psycopg2
import psycopg2.extras

SYMBOL = os.getenv("GOLD_SYMBOL", "GDU6@RTSX")
STRATEGY = "gold_short_only_shadow_v1"
BUCKETS = int(os.getenv("GOLD_WALKFORWARD_BUCKETS", "4"))

SQL = """
WITH signals AS (
    SELECT
        s.id,
        s.symbol,
        s.timeframe,
        s.signal_ts,
        s.side,
        s.entry_price::numeric AS entry_price,
        x.exit_ts,
        x.exit_price
    FROM runtime_shadow_gold_signals s
    LEFT JOIN LATERAL (
        SELECT
            b.ts AS exit_ts,
            b.close::numeric AS exit_price
        FROM market_bars b
        WHERE b.symbol = s.symbol
          AND b.timeframe = s.timeframe
          AND b.ts > s.signal_ts
        ORDER BY b.ts
        OFFSET 9
        LIMIT 1
    ) x ON true
    WHERE s.symbol=%s
      AND s.strategy=%s
),
scored AS (
    SELECT
        *,
        EXTRACT(
            EPOCH FROM (exit_ts - signal_ts)
        ) / 60.0 AS exit_gap_minutes,
        CASE
            WHEN exit_price IS NULL THEN NULL
            WHEN side='SELL' THEN entry_price - exit_price
            ELSE exit_price - entry_price
        END AS pnl
    FROM signals
)
SELECT *
FROM scored
WHERE pnl IS NOT NULL
ORDER BY signal_ts;
"""

def calc(rows):
    trades = len(rows)
    wins = sum(1 for r in rows if float(r["pnl"]) > 0)
    losses = sum(1 for r in rows if float(r["pnl"]) < 0)
    net = sum(float(r["pnl"]) for r in rows)
    gross_profit = sum(float(r["pnl"]) for r in rows if float(r["pnl"]) > 0)
    gross_loss = abs(sum(float(r["pnl"]) for r in rows if float(r["pnl"]) < 0))
    pf = gross_profit / gross_loss if gross_loss else None
    expectancy = net / trades if trades else 0.0
    winrate = wins / trades * 100 if trades else 0.0
    return trades, wins, losses, net, expectancy, winrate, pf

def main() -> None:
    print("=== RUNTIME SHADOW VALIDATION GOLD WALKFORWARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"buckets={BUCKETS}")
    print("exit_model=MARKET_BARS_M5_NEXT_10")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY))
            rows = cur.fetchall()

    total = len(rows)
    bucket_size = math.ceil(total / BUCKETS) if total else 0

    favorable = 0
    unfavorable = 0
    no_data = 0

    print("WALKFORWARD_ROWS")

    for bucket in range(1, BUCKETS + 1):
        start = (bucket - 1) * bucket_size
        end = min(bucket * bucket_size, total)
        part = rows[start:end]

        trades, wins, losses, net, expectancy, winrate, pf = calc(part)

        if trades < 5:
            status = "NO_DATA"
            no_data += 1
        elif expectancy > 0 and (pf is None or pf >= 1.2):
            status = "FAVORABLE"
            favorable += 1
        else:
            status = "UNFAVORABLE"
            unfavorable += 1

        print(
            "WALKFORWARD_ROW "
            f"bucket={bucket} "
            f"from_trade={start + 1 if part else 0} "
            f"to_trade={end if part else 0} "
            f"trades={trades} "
            f"wins={wins} "
            f"losses={losses} "
            f"net_pnl={round(net, 6)} "
            f"expectancy={round(expectancy, 6)} "
            f"winrate={round(winrate, 2)} "
            f"profit_factor={round(pf, 4) if pf is not None else None} "
            f"status={status}"
        )

    if total < 30:
        verdict = "GOLD_WALKFORWARD_NO_DATA"
    elif unfavorable == 0 and favorable >= max(1, BUCKETS - 1):
        verdict = "GOLD_WALKFORWARD_STABLE"
    elif favorable > unfavorable:
        verdict = "GOLD_WALKFORWARD_MIXED"
    else:
        verdict = "GOLD_WALKFORWARD_UNSTABLE"

    print()
    print(
        "WALKFORWARD_SUMMARY "
        f"closed_shadow_trades={total} "
        f"favorable={favorable} "
        f"unfavorable={unfavorable} "
        f"no_data={no_data}"
    )
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={verdict}")
    print("RUNTIME_SHADOW_VALIDATION_GOLD_WALKFORWARD_V1_OK")

if __name__ == "__main__":
    main()
