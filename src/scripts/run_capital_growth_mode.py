from __future__ import annotations

import os
import psycopg2

from finam_core.runtime.capital_growth_mode import CapitalGrowthMode


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)
    mode = CapitalGrowthMode()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select coalesce(margin_utilization_pct, 0)
                from portfolio_snapshots
                order by ts desc
                limit 1
            """)
            row = cur.fetchone()
            portfolio_heat = float(row[0] or 0.0) / 100.0 if row else 0.0

            cur.execute("""
                select
                    symbol,
                    raw_json->'runtime_decision'->>'trade_quality_grade',
                    raw_json->'runtime_decision'->>'trade_quality_score',
                    raw_json->'runtime_decision'->>'expected_value',
                    raw_json->'runtime_decision'->>'probability_tp',
                    raw_json->'runtime_decision'->>'probability_sl',
                    risk_reward
                from radar_candidate_analysis
                where source = 'watch_candidate_runtime_analyzer'
                  and decision = 'ALERT'
                order by created_at desc
                limit 20
            """)

            processed = 0
            allowed = 0

            for symbol, grade, score, ev, p_tp, p_sl, rr in cur.fetchall():
                decision = mode.decide(
                    trade_quality_grade=str(grade or "D"),
                    trade_quality_score=float(score or 0.0),
                    expected_value=float(ev or 0.0),
                    probability_tp=float(p_tp or 0.0),
                    probability_sl=float(p_sl or 0.0),
                    risk_reward=float(rr or 0.0),
                    portfolio_heat=portfolio_heat,
                    runtime_severity="INFO",
                )

                processed += 1
                if decision.allowed:
                    allowed += 1

                print(
                    "CAPITAL_GROWTH_DECISION "
                    f"symbol={symbol} "
                    f"allowed={decision.allowed} "
                    f"mode={decision.mode} "
                    f"risk_pct={decision.risk_pct:.4f} "
                    f"reason={decision.reason}",
                    flush=True,
                )

    print(
        f"CAPITAL_GROWTH_MODE_OK processed={processed} allowed={allowed}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
