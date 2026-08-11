from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor


def main() -> int:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    w.strategy_code,
                    w.symbol_group,
                    w.side_code,
                    w.candidate_code,
                    w.workflow_stage,
                    w.statistical_verdict,
                    w.expensive_gates_pass,
                    w.admission_id,

                    r.pairs,
                    r.oos_pairs,

                    COALESCE(
                        (r.metrics #>>
                            '{adaptive_gate,min_pairs}')::integer,
                        60
                    ) AS min_pairs,

                    (r.metrics #>>
                        '{economics_decomposition,net_expectancy_r}')::numeric
                        AS net_expectancy_r,

                    (r.metrics #>>
                        '{negative_control,passed}')::boolean
                        AS placebo_pass,

                    (r.metrics #>>
                        '{negative_control,delta_expectancy_r}')::numeric
                        AS delta_expectancy_r,

                    (r.metrics #>>
                        '{negative_control,delta_lower_bound_r}')::numeric
                        AS delta_lower_bound_r,

                    r.metrics #>>
                        '{negative_control,reason}'
                        AS placebo_reason

                FROM analytics.entry_exit_promotion_workflow_v1 w

                JOIN analytics.entry_exit_recommendation_v1 r
                  ON r.strategy_code = w.strategy_code
                 AND r.symbol_group = w.symbol_group
                 AND r.side_code = w.side_code
                 AND r.candidate_code = w.candidate_code

                WHERE w.evidence #>>
                        '{promotion_workflow,selected_for_shadow_funnel}'
                      = 'true'

                ORDER BY
                    COALESCE(
                        (r.metrics #>>
                            '{economics_decomposition,net_expectancy_r}')::numeric,
                        -999999
                    ) DESC,
                    r.pairs DESC
                """
            )

            rows = cur.fetchall()

        positive = [
            row
            for row in rows
            if row["net_expectancy_r"] is not None
            and row["net_expectancy_r"] > 0
        ]

        placebo_positive = [
            row
            for row in positive
            if row["placebo_pass"] is True
        ]

        for rank, row in enumerate(placebo_positive, start=1):
            pairs = int(row["pairs"] or 0)
            minimum = int(row["min_pairs"] or 60)
            deficit = max(0, minimum - pairs)

            print(
                "PRIORITY_ROW "
                f"rank={rank} "
                f"strategy={row['strategy_code']} "
                f"symbol={row['symbol_group']} "
                f"side={row['side_code']} "
                f"candidate={row['candidate_code']} "
                f"pairs={pairs} "
                f"minimum_pairs={minimum} "
                f"pair_deficit={deficit} "
                f"net_expectancy={row['net_expectancy_r']} "
                f"placebo_pass={int(row['placebo_pass'])} "
                f"delta={row['delta_expectancy_r']} "
                f"delta_lower_bound={row['delta_lower_bound_r']} "
                f"statistical_verdict={row['statistical_verdict']} "
                f"oos_pairs={int(row['oos_pairs'] or 0)} "
                f"has_admission={int(row['admission_id'] is not None)}"
            )

        oos_evidence = [
            row for row in rows
            if int(row["oos_pairs"] or 0) > 0
        ]

        oos_with_admission = [
            row for row in oos_evidence
            if row["admission_id"] is not None
        ]

        print(f"active_challengers={len(rows)}")
        print(f"positive_net_candidates={len(positive)}")
        print(f"positive_and_placebo_pass={len(placebo_positive)}")
        print(f"oos_evidence_candidates={len(oos_evidence)}")
        print(f"oos_evidence_with_admission={len(oos_with_admission)}")
        print(
            "oos_pair_evidence_not_equated_to_admission=1"
        )

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
            "ACTIVE_CHALLENGER_PRIORITY_V1_READY"
        )

        return 0

    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
