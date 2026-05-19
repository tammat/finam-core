from __future__ import annotations

import os
import psycopg2

from finam_core.runtime.capital_growth_regime_allocator import (
    CapitalGrowthRegimeAllocator,
)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
                select
                    coalesce(drawdown, 0),
                    coalesce(equity, 0)
                from portfolio_snapshots
                order by ts desc
                limit 1
            """)

            row = cur.fetchone()

            drawdown_value = abs(float(row[0] or 0.0)) if row else 0.0
            equity = abs(float(row[1] or 0.0)) if row else 0.0
            drawdown_pct = (drawdown_value / equity) if equity > 0 else 0.0

            cur.execute("""
                select
                    count(*) filter (
                        where coalesce((raw_json->'runtime_decision'->>'expected_value')::float, 0) > 0
                    )::float
                    /
                    greatest(count(*), 1)::float as winrate_proxy
                from radar_candidate_analysis
                where source = 'watch_candidate_runtime_analyzer'
                  and created_at >= now() - interval '1 day'
            """)

            winrate_row = cur.fetchone()
            winrate = float(winrate_row[0] or 0.0)

            cur.execute("""
                select
                    count(*) filter (where decision = 'ALERT')::float
                    /
                    greatest(count(*), 1)::float as market_breadth_proxy
                from radar_candidate_analysis
                where source = 'watch_candidate_runtime_analyzer'
                  and created_at >= now() - interval '60 minutes'
            """)

            breadth_row = cur.fetchone()
            breadth = float(breadth_row[0] or 0.0)

            cur.execute("""
                select count(*)
                from portfolio_reconciliation_events
                where severity = 'HIGH'
                  and coalesce(is_archived, false) = false
                  and created_at >= now() - interval '60 minutes'
            """)

            stress_issues = int(cur.fetchone()[0] or 0)
            stress = "HIGH" if stress_issues > 0 else "INFO"

            cur.execute("""
                select
                    coalesce(regime, 'unknown')
                from runtime_active_universe
                order by updated_at desc
                limit 1
            """)

            regime_row = cur.fetchone()
            regime = str(regime_row[0] or "unknown")

            decision = CapitalGrowthRegimeAllocator().decide(
                runtime_regime=regime,
                portfolio_drawdown_pct=drawdown_pct,
                runtime_winrate=winrate,
                runtime_stress_level=stress,
                market_breadth=breadth,
            )

            print(
                "CAPITAL_GROWTH_REGIME_ALLOCATOR "
                f"profile={decision.profile} "
                f"reason={decision.reason}",
                flush=True,
            )

            os.environ["CAPITAL_GROWTH_PROFILE"] = decision.profile

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
