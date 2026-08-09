#!/usr/bin/env python3
from __future__ import annotations

import math
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


SYMBOL = os.getenv("GOLD_SYMBOL", "GDU6@RTSX")
STRATEGY = "gold_short_only_shadow_v1"
BUCKETS = int(os.getenv("GOLD_WALKFORWARD_BUCKETS", "4"))

# Диагностика использует ту же exit-модель, что и исправленный walk-forward:
# десятый следующий существующий M5 market bar.
SQL = """
WITH signal_base AS (
    SELECT
        s.id,
        s.symbol,
        s.timeframe,
        s.signal_ts,
        s.side,
        s.entry_price::numeric AS entry_price,

        x.exit_ts,
        x.exit_price,

        -- Рыночный контекст непосредственно перед сигналом.
        ctx.bar_ts,
        ctx.close_price,
        ctx.atr14,
        ctx.sma20,
        ctx.sma50

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

    LEFT JOIN LATERAL (
        SELECT
            z.ts AS bar_ts,
            z.close_price,
            z.atr14,
            z.sma20,
            z.sma50
        FROM (
            SELECT
                b.ts,
                b.close::numeric AS close_price,

                avg((b.high - b.low)::numeric)
                    OVER (
                        ORDER BY b.ts
                        ROWS BETWEEN 13 PRECEDING AND CURRENT ROW
                    ) AS atr14,

                avg(b.close::numeric)
                    OVER (
                        ORDER BY b.ts
                        ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                    ) AS sma20,

                avg(b.close::numeric)
                    OVER (
                        ORDER BY b.ts
                        ROWS BETWEEN 49 PRECEDING AND CURRENT ROW
                    ) AS sma50

            FROM market_bars b
            WHERE b.symbol = s.symbol
              AND b.timeframe = s.timeframe
              AND b.ts <= s.signal_ts
            ORDER BY b.ts DESC
            LIMIT 60
        ) z
        ORDER BY z.ts DESC
        LIMIT 1
    ) ctx ON true

    WHERE s.symbol = %s
      AND s.strategy = %s
),

scored AS (
    SELECT
        *,

        CASE
            WHEN exit_price IS NULL THEN NULL
            WHEN side = 'SELL' THEN entry_price - exit_price
            ELSE exit_price - entry_price
        END AS pnl,

        CASE
            WHEN sma20 IS NULL OR sma50 IS NULL THEN 'NO_DATA'
            WHEN sma20 > sma50 THEN 'UP'
            WHEN sma20 < sma50 THEN 'DOWN'
            ELSE 'FLAT'
        END AS trend_regime,

        CASE
            -- UTC. Границы намеренно простые и диагностические.
            WHEN EXTRACT(HOUR FROM signal_ts) < 7 THEN 'EARLY'
            WHEN EXTRACT(HOUR FROM signal_ts) < 12 THEN 'MORNING'
            WHEN EXTRACT(HOUR FROM signal_ts) < 16 THEN 'MAIN'
            ELSE 'LATE'
        END AS session_code

    FROM signal_base
),

valid AS (
    SELECT *
    FROM scored
    WHERE pnl IS NOT NULL
),

numbered AS (
    SELECT
        *,
        row_number() OVER (ORDER BY signal_ts) AS rn,
        count(*) OVER () AS total
    FROM valid
),

bucketed AS (
    SELECT
        *,
        least(
            %s,
            ceil(rn * %s::numeric / total)::int
        ) AS bucket
    FROM numbered
),

with_density AS (
    SELECT
        b.*,

        (
            SELECT count(*)
            FROM runtime_shadow_gold_signals d
            WHERE d.symbol = b.symbol
              AND d.strategy = %s
              AND d.signal_ts > b.signal_ts - interval '60 minutes'
              AND d.signal_ts <= b.signal_ts
        ) AS signals_60m

    FROM bucketed b
)

SELECT *
FROM with_density
ORDER BY signal_ts
"""


def f(value) -> float | None:
    if value is None:
        return None
    return float(value)


def profit_factor(rows: list[dict]) -> float | None:
    gp = sum(f(r["pnl"]) or 0.0 for r in rows if (f(r["pnl"]) or 0) > 0)
    gl = abs(sum(f(r["pnl"]) or 0.0 for r in rows if (f(r["pnl"]) or 0) < 0))
    return gp / gl if gl else None


def status(expectancy: float, pf: float | None, trades: int) -> str:
    if trades < 5:
        return "NO_DATA"
    if expectancy > 0 and (pf is None or pf >= 1.2):
        return "FAVORABLE"
    return "UNFAVORABLE"


def main() -> int:
    print("=== GOLD WALKFORWARD REGIME DIAGNOSTICS V1 ===")
    print("mode=research_read_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("orders_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print(f"buckets={BUCKETS}")
    print("exit_model=MARKET_BARS_M5_NEXT_10")
    print("cost_model=NOT_APPLIED_SOURCE_NOT_CONFIRMED")
    print()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                SQL,
                (
                    SYMBOL,
                    STRATEGY,
                    BUCKETS,
                    BUCKETS,
                    STRATEGY,
                ),
            )
            rows = [dict(r) for r in cur.fetchall()]

        print("BUCKET_ROWS")

        for bucket in range(1, BUCKETS + 1):
            part = [r for r in rows if r["bucket"] == bucket]

            trades = len(part)
            net = sum(f(r["pnl"]) or 0.0 for r in part)
            exp = net / trades if trades else 0.0
            pf = profit_factor(part)

            atr_values = [f(r["atr14"]) for r in part if f(r["atr14"]) is not None]
            density_values = [
                int(r["signals_60m"])
                for r in part
                if r["signals_60m"] is not None
            ]

            avg_atr = (
                sum(atr_values) / len(atr_values)
                if atr_values else None
            )
            avg_density = (
                sum(density_values) / len(density_values)
                if density_values else None
            )

            print(
                "BUCKET_ROW "
                f"bucket={bucket} "
                f"trades={trades} "
                f"net_pnl={net:.6f} "
                f"expectancy={exp:.6f} "
                f"profit_factor={pf:.4f} "
                if pf is not None
                else
                "BUCKET_ROW "
                f"bucket={bucket} "
                f"trades={trades} "
                f"net_pnl={net:.6f} "
                f"expectancy={exp:.6f} "
                f"profit_factor=None "
                f"status={status(exp, pf, trades)} "
                f"avg_atr14={avg_atr:.6f} "
                if avg_atr is not None
                else
                "BUCKET_ROW "
                f"bucket={bucket} "
                f"trades={trades} "
                f"net_pnl={net:.6f} "
                f"expectancy={exp:.6f} "
                f"profit_factor={pf:.4f} "
                f"status={status(exp, pf, trades)} "
                f"avg_atr14=None "
            )

            # Отдельная строка контекста, чтобы не смешивать экономику и режимы.
            trends = {}
            sessions = {}

            for r in part:
                trends[r["trend_regime"]] = trends.get(r["trend_regime"], 0) + 1
                sessions[r["session_code"]] = sessions.get(r["session_code"], 0) + 1

            trend_text = ",".join(
                f"{k}:{v}" for k, v in sorted(trends.items())
            )
            session_text = ",".join(
                f"{k}:{v}" for k, v in sorted(sessions.items())
            )

            print(
                "BUCKET_CONTEXT "
                f"bucket={bucket} "
                f"trend={trend_text or 'NO_DATA'} "
                f"session={session_text or 'NO_DATA'} "
                f"avg_signals_60m="
                f"{avg_density:.4f}"
                if avg_density is not None
                else
                "BUCKET_CONTEXT "
                f"bucket={bucket} "
                f"trend={trend_text or 'NO_DATA'} "
                f"session={session_text or 'NO_DATA'} "
                f"avg_signals_60m=None"
            )

        print()
        print("REGIME_BREAKDOWN")

        for dimension in ("trend_regime", "session_code"):
            values = sorted({r[dimension] for r in rows})

            for value in values:
                part = [r for r in rows if r[dimension] == value]
                trades = len(part)
                net = sum(f(r["pnl"]) or 0.0 for r in part)
                exp = net / trades if trades else 0.0
                pf = profit_factor(part)

                print(
                    "REGIME_ROW "
                    f"dimension={dimension} "
                    f"value={value} "
                    f"trades={trades} "
                    f"net_pnl={net:.6f} "
                    f"expectancy={exp:.6f} "
                    f"profit_factor="
                    f"{pf:.4f}" if pf is not None else
                    "REGIME_ROW "
                    f"dimension={dimension} "
                    f"value={value} "
                    f"trades={trades} "
                    f"net_pnl={net:.6f} "
                    f"expectancy={exp:.6f} "
                    f"profit_factor=None"
                )

        print()
        print(f"rows={len(rows)}")
        print("db_writes_performed=0")
        print("runtime_allow=0")
        print("execution_enabled=0")
        print("VERDICT=GOLD_WALKFORWARD_REGIME_DIAGNOSTICS_READY")

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
