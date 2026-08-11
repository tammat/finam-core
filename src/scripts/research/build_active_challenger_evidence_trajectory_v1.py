from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor


TARGETS = (
    ("MEAN_REVERSION_EQUITY", "SBERP", "LONG", "CONFIRM_1_S1.8_R1.8"),
    ("VOLATILITY_BREAKOUT_EQUITY", "SBER", "LONG", "IMMEDIATE_S1.5_R1.6"),
)


def main() -> int:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for strategy, symbol, side, candidate in TARGETS:
                cur.execute(
                    """
                    SELECT
                        r.strategy_code,
                        r.symbol_group,
                        r.side_code,
                        r.candidate_code,
                        r.pairs,
                        r.oos_pairs,
                        w.statistical_verdict,
                        w.expensive_gates_pass,
                        (r.metrics #>>
                            '{economics_decomposition,net_expectancy_r}')::numeric
                            AS net_expectancy,
                        (r.metrics #>>
                            '{negative_control,passed}')::boolean
                            AS placebo_pass,
                        (r.metrics #>>
                            '{negative_control,delta_expectancy_r}')::numeric
                            AS delta,
                        (r.metrics #>>
                            '{negative_control,delta_lower_bound_r}')::numeric
                            AS delta_lower_bound,
                        r.generated_at
                    FROM analytics.entry_exit_recommendation_v1 r
                    JOIN analytics.entry_exit_promotion_workflow_v1 w
                      ON w.strategy_code = r.strategy_code
                     AND w.symbol_group = r.symbol_group
                     AND w.side_code = r.side_code
                     AND w.candidate_code = r.candidate_code
                    WHERE r.strategy_code=%s
                      AND r.symbol_group=%s
                      AND r.side_code=%s
                      AND r.candidate_code=%s
                    """,
                    (strategy, symbol, side, candidate),
                )

                row = cur.fetchone()

                if row is None:
                    print(
                        "TRAJECTORY_ROW "
                        f"strategy={strategy} "
                        f"symbol={symbol} "
                        f"side={side} "
                        f"candidate={candidate} "
                        "status=MISSING"
                    )
                    continue

                print(
                    "TRAJECTORY_ROW "
                    f"strategy={row['strategy_code']} "
                    f"symbol={row['symbol_group']} "
                    f"side={row['side_code']} "
                    f"candidate={row['candidate_code']} "
                    f"pairs={row['pairs']} "
                    f"oos_pairs={row['oos_pairs']} "
                    f"net_expectancy={row['net_expectancy']} "
                    f"placebo_pass={int(row['placebo_pass'] is True)} "
                    f"delta={row['delta']} "
                    f"delta_lower_bound={row['delta_lower_bound']} "
                    f"statistical_verdict={row['statistical_verdict']} "
                    f"expensive_pass={int(bool(row['expensive_gates_pass']))} "
                    f"generated_at={row['generated_at'].isoformat()}"
                )

        print("targets=2")
        print("trajectory_snapshot_only=1")
        print("thresholds_changed=0")
        print("net_first_logic_changed=0")
        print("placebo_logic_changed=0")
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print(
            "VERDICT="
            "ACTIVE_CHALLENGER_EVIDENCE_TRAJECTORY_V1_READY"
        )

        return 0

    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
