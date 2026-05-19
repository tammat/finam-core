from __future__ import annotations

import os
import psycopg2

from finam_core.runtime.runtime_capital_allocator import RuntimeCapitalAllocator


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)
    allocator = RuntimeCapitalAllocator()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select equity, cash, coalesce(margin_utilization_pct, 0), coalesce(drawdown, 0)
                from portfolio_snapshots
                order by ts desc
                limit 1
            """)
            portfolio = cur.fetchone()

            if portfolio is None:
                print("RUNTIME_CAPITAL_ALLOCATOR_SKIP reason=no_portfolio_snapshot", flush=True)
                return 0

            equity, cash, margin_utilization_pct, drawdown = map(float, portfolio)

            cur.execute("""
                select
                    symbol,
                    score,
                    risk_reward,
                    coalesce(raw_json->'runtime_decision'->>'active_group_alerts', '0')::int as correlation_pressure
                from radar_candidate_analysis
                where source = 'watch_candidate_runtime_analyzer'
                  and decision = 'ALERT'
                order by created_at desc
                limit 20
            """)

            rows = cur.fetchall()

            for symbol, score, risk_reward, correlation_pressure in rows:
                decision = allocator.allocate(
                    equity=equity,
                    cash=cash,
                    margin_utilization_pct=margin_utilization_pct,
                    drawdown=drawdown,
                    signal_score=float(score or 0),
                    risk_reward=float(risk_reward or 0),
                    correlation_pressure=int(correlation_pressure or 0),
                    runtime_severity="INFO",
                )

                print(
                    "RUNTIME_CAPITAL_ALLOCATION "
                    f"symbol={symbol} "
                    f"allowed={decision.allowed} "
                    f"risk_multiplier={decision.risk_multiplier} "
                    f"max_position_value={decision.max_position_value} "
                    f"reason={decision.reason}",
                    flush=True,
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
