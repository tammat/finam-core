from __future__ import annotations

import os

import psycopg2

from finam_core.runtime.adaptive_portfolio_allocator import (
    AdaptivePortfolioAllocator,
)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    allocator = AdaptivePortfolioAllocator()

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
                select
                    coalesce(free_margin, 0),
                    coalesce(margin_utilization_pct, 0)
                from portfolio_snapshots
                order by ts desc
                limit 1
            """)

            portfolio = cur.fetchone()

            if portfolio is None:
                print("ADAPTIVE_ALLOCATOR_SKIP no_portfolio", flush=True)
                return 0

            free_margin = float(portfolio[0] or 0.0)
            margin_utilization_pct = float(portfolio[1] or 0.0)

            portfolio_heat = margin_utilization_pct / 100.0

            cur.execute("""
                select
                    symbol,
                    entry_price,
                    raw_json->'runtime_decision'->>'trade_quality_score' as quality_score,
                    raw_json->'runtime_decision'->>'trade_quality_grade' as quality_grade,
                    raw_json->'runtime_decision'->>'expected_value' as expected_value,
                    coalesce(raw_json->'runtime_decision'->>'active_group_alerts', '0')::int as correlation_pressure
                from radar_candidate_analysis
                where source = 'watch_candidate_runtime_analyzer'
                  and decision = 'ALERT'
                order by created_at desc
                limit 20
            """)

            rows = cur.fetchall()

            for row in rows:
                (
                    symbol,
                    entry_price,
                    quality_score,
                    quality_grade,
                    expected_value,
                    correlation_pressure,
                ) = row

                cur.execute("""
                    select count(*)
                    from real_portfolio_positions
                    where symbol = %s
                """, (symbol,))

                existing_position = int(cur.fetchone()[0] or 0) > 0

                decision = allocator.allocate(
                    symbol=str(symbol),
                    entry_price=float(entry_price or 0.0),

                    quality_score=float(quality_score or 0.0),
                    quality_grade=str(quality_grade or "D"),

                    expected_value=float(expected_value or 0.0),

                    available_capital=free_margin,
                    portfolio_heat=portfolio_heat,

                    correlation_pressure=int(correlation_pressure or 0),
                    existing_position=existing_position,
                )

                print(
                    "ADAPTIVE_PORTFOLIO_DECISION "
                    f"symbol={decision.symbol} "
                    f"allowed={decision.allowed} "
                    f"capital={decision.allocated_capital} "
                    f"qty={decision.allocated_qty} "
                    f"grade={decision.grade} "
                    f"score={decision.quality_score} "
                    f"reason={decision.reason}",
                    flush=True,
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
