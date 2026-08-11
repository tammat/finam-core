from __future__ import annotations

import os
from decimal import Decimal

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

                    COALESCE(
                        (r.metrics #>>
                            '{adaptive_gate,min_oos}')::integer,
                        15
                    ) AS min_oos,

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

                    r.metrics #>>
                        '{negative_control,reason}'
                        AS placebo_reason,

                    r.generated_at

                FROM analytics.entry_exit_promotion_workflow_v1 w

                JOIN analytics.entry_exit_recommendation_v1 r
                  ON r.strategy_code = w.strategy_code
                 AND r.symbol_group = w.symbol_group
                 AND r.side_code = w.side_code
                 AND r.candidate_code = w.candidate_code

                WHERE w.evidence #>>
                    '{promotion_workflow,selected_for_shadow_funnel}'
                    = 'true'
                """
            )

            rows = cur.fetchall()

        ranked = []

        for row in rows:
            pairs = int(row["pairs"] or 0)
            min_pairs = int(row["min_pairs"] or 60)

            net = row["net_expectancy"]
            placebo_pass = row["placebo_pass"] is True
            delta_lb = row["delta_lower_bound"]

            positive_net = (
                net is not None and net > 0
            )

            positive_delta_lb = (
                delta_lb is not None
                and delta_lb > 0
            )

            sample_completion = (
                Decimal(pairs)
                / Decimal(min_pairs)
                if min_pairs > 0
                else Decimal("0")
            )

            if (
                pairs >= min_pairs
                and positive_net
                and placebo_pass
                and positive_delta_lb
            ):
                research_state = "VALIDATION_CANDIDATE"
                state_rank = 0

            elif (
                positive_net
                and placebo_pass
                and positive_delta_lb
            ):
                research_state = "EARLY_POSITIVE_SIGNAL"
                state_rank = 1

            else:
                research_state = "NO_CURRENT_EDGE_SIGNAL"
                state_rank = 2

            ranked.append(
                {
                    **row,
                    "sample_completion": sample_completion,
                    "research_state": research_state,
                    "state_rank": state_rank,
                    "positive_net": positive_net,
                    "positive_delta_lb": positive_delta_lb,
                }
            )

        ranked.sort(
            key=lambda row: (
                row["state_rank"],
                -row["sample_completion"],
                -int(row["pairs"] or 0),
                -Decimal(str(row["net_expectancy"] or 0)),
            )
        )

        visible = [
            row
            for row in ranked
            if row["research_state"]
            != "NO_CURRENT_EDGE_SIGNAL"
        ]

        for rank, row in enumerate(visible, start=1):
            completion_pct = (
                row["sample_completion"]
                * Decimal("100")
            )

            print(
                "EVIDENCE_PRIORITY_ROW "
                f"rank={rank} "
                f"state={row['research_state']} "
                f"strategy={row['strategy_code']} "
                f"symbol={row['symbol_group']} "
                f"side={row['side_code']} "
                f"candidate={row['candidate_code']} "
                f"pairs={int(row['pairs'] or 0)} "
                f"minimum_pairs={int(row['min_pairs'] or 60)} "
                f"sample_completion_pct={completion_pct:.2f} "
                f"net_expectancy={row['net_expectancy']} "
                f"placebo_pass={int(row['placebo_pass'] is True)} "
                f"delta={row['delta']} "
                f"delta_lower_bound={row['delta_lower_bound']} "
                f"statistical_verdict={row['statistical_verdict']} "
                f"expensive_pass={int(bool(row['expensive_gates_pass']))} "
                f"oos_pairs={int(row['oos_pairs'] or 0)} "
                f"has_admission={int(row['admission_id'] is not None)}"
            )

        print(f"active_challengers={len(rows)}")
        print(f"evidence_priority_candidates={len(visible)}")

        validation = sum(
            1
            for row in visible
            if row["research_state"]
            == "VALIDATION_CANDIDATE"
        )

        early = sum(
            1
            for row in visible
            if row["research_state"]
            == "EARLY_POSITIVE_SIGNAL"
        )

        print(f"validation_candidates={validation}")
        print(f"early_positive_signals={early}")

        print("v1_rank_used_for_edge_strength=0")
        print("sample_maturity_used_for_priority=1")
        print("positive_net_required=1")
        print("placebo_pass_required=1")
        print("positive_delta_lower_bound_required=1")

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
            "ACTIVE_CHALLENGER_EVIDENCE_PRIORITY_V2_READY"
        )

        return 0

    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
