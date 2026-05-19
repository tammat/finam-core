from __future__ import annotations

import os
import psycopg2

from finam_core.runtime.autonomous_portfolio_brain import (
    AutonomousPortfolioBrain,
)


def scalar(cur, sql: str):
    cur.execute(sql)
    row = cur.fetchone()
    if not row:
        return 0
    return row[0]


def main() -> int:

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:

            cur.execute("""
                select
                    coalesce(equity, 0),
                    coalesce(drawdown, 0),
                    coalesce(realized_pnl, 0) + coalesce(unrealized_pnl, 0)
                from portfolio_snapshots
                order by ts desc
                limit 1
            """)

            row = cur.fetchone()

            equity = float(row[0] or 0)
            drawdown_value = abs(float(row[1] or 0))
            daily_pnl = float(row[2] or 0)

            drawdown_pct = (
                drawdown_value / equity
                if equity > 0 else 0
            )

            daily_pnl_pct = (
                daily_pnl / equity
                if equity > 0 else 0
            )

            open_positions = int(scalar(cur, """
                select count(*)
                from real_portfolio_positions
                where abs(coalesce(qty, 0)) > 0
            """))

            winrate = float(scalar(cur, """
                select
                    count(*) filter (
                        where coalesce((raw_json->'runtime_decision'->>'expected_value')::float, 0) > 0
                    )::float
                    /
                    greatest(count(*), 1)::float
                from radar_candidate_analysis
                where created_at >= now() - interval '1 day'
            """))

            breadth = float(scalar(cur, """
                select
                    count(*) filter (
                        where decision='ALERT'
                    )::float
                    /
                    greatest(count(*), 1)::float
                from radar_candidate_analysis
                where created_at >= now() - interval '60 minutes'
            """))

            stress_events = int(scalar(cur, """
                select count(*)
                from portfolio_reconciliation_events
                where severity='HIGH'
                  and coalesce(is_archived,false)=false
                  and created_at >= now() - interval '60 minutes'
            """))

            stress = "HIGH" if stress_events > 0 else "INFO"

            regime = str(scalar(cur, """
                select coalesce(regime, 'range')
                from runtime_active_universe
                order by updated_at desc
                limit 1
            """))

            decision = AutonomousPortfolioBrain().decide(
                equity=equity,
                drawdown_pct=drawdown_pct,
                runtime_winrate=winrate,
                market_breadth=breadth,
                runtime_stress=stress,
                open_positions=open_positions,
                daily_pnl_pct=daily_pnl_pct,
                regime=regime,
            )

            print(
                "AUTONOMOUS_PORTFOLIO_BRAIN "
                f"phase={decision.portfolio_phase} "
                f"profile={decision.growth_profile} "
                f"risk={decision.max_risk_per_trade:.4f} "
                f"capital_pressure={decision.capital_pressure:.2f} "
                f"reason={decision.reason}",
                flush=True,
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
