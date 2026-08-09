#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg2
import psycopg2.extras


CONFIG = Path("config/research/gold_up_regime_frozen_v1.json")


def profit_factor(rows):
    gross_profit = sum(float(r["pnl"]) for r in rows if r["pnl"] > 0)
    gross_loss = abs(sum(float(r["pnl"]) for r in rows if r["pnl"] < 0))
    return gross_profit / gross_loss if gross_loss else None


def main() -> int:
    cfg = json.loads(CONFIG.read_text())

    symbol = cfg["symbol"]
    strategy = cfg["strategy"]
    boundary = cfg["freeze_boundary_exclusive"]
    minimum = int(cfg["oos_policy"]["minimum_oos_trades"])
    min_pf = float(cfg["oos_policy"]["pass_profit_factor_gte"])

    print("=== GOLD UP REGIME FROZEN OOS V1 ===")
    print("mode=prospective_oos_read_only")
    print(f"hypothesis={cfg['hypothesis_code']}")
    print(f"freeze_boundary_exclusive={boundary}")
    print("development_rows_allowed=0")
    print("regime_rule=SMA20_GT_SMA50")
    print("exit_model=MARKET_BARS_M5_NEXT_10")
    print("execution=disabled")
    print("runtime_changed=0")

    sql = """
    WITH candidates AS (
        SELECT
            s.signal_ts,
            s.side,
            s.entry_price::numeric AS entry_price,

            exit_bar.exit_price,

            ctx.sma20,
            ctx.sma50

        FROM runtime_shadow_gold_signals s

        LEFT JOIN LATERAL (
            SELECT b.close::numeric AS exit_price
            FROM market_bars b
            WHERE b.symbol=s.symbol
              AND b.timeframe=s.timeframe
              AND b.ts>s.signal_ts
            ORDER BY b.ts
            OFFSET 9
            LIMIT 1
        ) exit_bar ON true

        LEFT JOIN LATERAL (
            SELECT
                q.sma20,
                q.sma50
            FROM (
                SELECT
                    b.ts,
                    avg(b.close::numeric) OVER (
                        ORDER BY b.ts
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS sma20,
                    avg(b.close::numeric) OVER (
                        ORDER BY b.ts
                        ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
                    ) AS sma50
                FROM market_bars b
                WHERE b.symbol=s.symbol
                  AND b.timeframe=s.timeframe
                  AND b.ts<=s.signal_ts
                ORDER BY b.ts DESC
                LIMIT 60
            ) q
            ORDER BY q.ts DESC
            LIMIT 1
        ) ctx ON true

        WHERE s.symbol=%s
          AND s.strategy=%s
          AND s.signal_ts>%s::timestamptz
    ),

    scored AS (
        SELECT
            *,
            CASE
                WHEN exit_price IS NULL THEN NULL
                WHEN side='SELL'
                    THEN entry_price-exit_price
                ELSE exit_price-entry_price
            END AS pnl
        FROM candidates
        WHERE sma20>sma50
    )

    SELECT signal_ts, pnl
    FROM scored
    WHERE pnl IS NOT NULL
    ORDER BY signal_ts
    """

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(sql, (symbol, strategy, boundary))
            rows = [dict(r) for r in cur.fetchall()]

        trades = len(rows)
        net = sum(float(r["pnl"]) for r in rows)
        expectancy = net / trades if trades else 0.0
        pf = profit_factor(rows)

        print()
        print(
            "OOS_ROW "
            f"trades={trades} "
            f"net_pnl={net:.6f} "
            f"expectancy={expectancy:.6f} "
            f"profit_factor={pf:.4f}"
            if pf is not None
            else
            "OOS_ROW "
            f"trades={trades} "
            f"net_pnl={net:.6f} "
            f"expectancy={expectancy:.6f} "
            "profit_factor=None"
        )

        if trades < minimum:
            verdict = "GOLD_UP_REGIME_OOS_ACCUMULATING"
        elif expectancy > 0 and pf is not None and pf >= min_pf:
            verdict = "GOLD_UP_REGIME_OOS_PASS"
        else:
            verdict = "GOLD_UP_REGIME_OOS_FAIL"

        print(f"minimum_oos_trades={minimum}")
        print(f"runtime_allow=0")
        print(f"execution_enabled=0")
        print(f"VERDICT={verdict}")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
