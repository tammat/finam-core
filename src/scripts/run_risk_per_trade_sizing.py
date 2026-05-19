from __future__ import annotations

import os
import psycopg2

from finam_core.runtime.capital_growth_mode import CapitalGrowthMode
from finam_core.runtime.risk_per_trade_sizing import RiskPerTradeSizer


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    conn = psycopg2.connect(dsn)
    growth = CapitalGrowthMode()
    sizer = RiskPerTradeSizer()

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    coalesce(equity, 0),
                    coalesce(margin_utilization_pct, 0)
                from portfolio_snapshots
                order by ts desc
                limit 1
            """)
            row = cur.fetchone()

            if row is None:
                print("RISK_PER_TRADE_SIZING_SKIP no_portfolio_snapshot", flush=True)
                return 0

            equity = float(row[0] or 0.0)
            portfolio_heat = float(row[1] or 0.0) / 100.0

            cur.execute("""
                select
                    symbol,
                    entry_price,
                    stop_loss,
                    raw_json->'runtime_decision'->>'max_position_value',
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

            for row in cur.fetchall():
                (
                    symbol,
                    entry_price,
                    stop_loss,
                    max_position_value,
                    grade,
                    score,
                    ev,
                    p_tp,
                    p_sl,
                    rr,
                ) = row

                growth_decision = growth.decide(
                    trade_quality_grade=str(grade or "D"),
                    trade_quality_score=float(score or 0.0),
                    expected_value=float(ev or 0.0),
                    probability_tp=float(p_tp or 0.0),
                    probability_sl=float(p_sl or 0.0),
                    risk_reward=float(rr or 0.0),
                    portfolio_heat=portfolio_heat,
                    runtime_severity="INFO",
                )

                size = sizer.size(
                    equity=equity,
                    risk_pct=growth_decision.risk_pct,
                    entry_price=float(entry_price or 0.0),
                    stop_loss=float(stop_loss or 0.0),
                    max_position_value=float(max_position_value or 0.0),
                )

                processed += 1
                if size.allowed:
                    allowed += 1

                print(
                    "RISK_PER_TRADE_SIZE "
                    f"symbol={symbol} "
                    f"growth_allowed={growth_decision.allowed} "
                    f"mode={growth_decision.mode} "
                    f"risk_pct={growth_decision.risk_pct:.4f} "
                    f"qty={size.qty} "
                    f"risk_rub={size.risk_rub} "
                    f"risk_per_unit={size.risk_per_unit} "
                    f"capital_used={size.capital_used} "
                    f"reason={size.reason}",
                    flush=True,
                )

    print(
        f"RISK_PER_TRADE_SIZING_OK processed={processed} allowed={allowed}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
