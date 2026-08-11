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
                    w.statistical_verdict,

                    r.pairs,

                    COALESCE(
                        (r.metrics #>>
                            '{adaptive_gate,min_pairs}')::integer,
                        60
                    ) AS min_pairs,

                    (r.metrics #>>
                        '{economics_decomposition,net_expectancy_r}')::numeric
                        AS net_expectancy,

                    (r.metrics #>>
                        '{negative_control,passed}')::boolean
                        AS placebo_pass,

                    (r.metrics #>>
                        '{negative_control,delta_lower_bound_r}')::numeric
                        AS placebo_delta_lower_bound,

                    (r.metrics #>>
                        '{statistical_gate,paired_expectancy_gain_r}')::numeric
                        AS paired_gain,

                    (r.metrics #>>
                        '{statistical_gate,probability_positive}')::numeric
                        AS paired_probability_positive,

                    r.metrics #>>
                        '{statistical_gate,reason}'
                        AS statistical_reason

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

        classified = []

        for row in rows:
            pairs = int(row["pairs"] or 0)
            min_pairs = int(row["min_pairs"] or 60)

            net = row["net_expectancy"]
            placebo_pass = row["placebo_pass"] is True
            placebo_lb = row["placebo_delta_lower_bound"]
            paired_gain = row["paired_gain"]

            positive_net = net is not None and net > 0
            positive_placebo_lb = placebo_lb is not None and placebo_lb > 0
            positive_paired_gain = paired_gain is not None and paired_gain > 0

            sample_completion = (
                Decimal(pairs) / Decimal(min_pairs)
                if min_pairs > 0
                else Decimal("0")
            )

            if (
                positive_net
                and placebo_pass
                and positive_placebo_lb
                and positive_paired_gain
                and pairs >= min_pairs
            ):
                state = "VALIDATION_CANDIDATE"
                state_rank = 0

            elif (
                positive_net
                and placebo_pass
                and positive_placebo_lb
                and positive_paired_gain
            ):
                state = "EARLY_BASELINE_SUPERIOR_SIGNAL"
                state_rank = 1

            elif (
                positive_net
                and placebo_pass
                and positive_placebo_lb
                and paired_gain is not None
                and paired_gain <= 0
            ):
                state = "POSITIVE_ABSOLUTE_BUT_BASELINE_INFERIOR"
                state_rank = 2

            elif (
                positive_net
                and placebo_pass
                and positive_placebo_lb
                and paired_gain is None
            ):
                state = "INSUFFICIENT_PAIRED_EVIDENCE"
                state_rank = 3

            else:
                state = "NO_CURRENT_EDGE_SIGNAL"
                state_rank = 4

            classified.append(
                {
                    **row,
                    "state": state,
                    "state_rank": state_rank,
                    "sample_completion": sample_completion,
                }
            )

        visible = [
            row for row in classified
            if row["state"] != "NO_CURRENT_EDGE_SIGNAL"
        ]

        visible.sort(
            key=lambda row: (
                row["state_rank"],
                -row["sample_completion"],
                -int(row["pairs"] or 0),
            )
        )

        for rank, row in enumerate(visible, start=1):
            completion_pct = row["sample_completion"] * Decimal("100")

            print(
                "EVIDENCE_V3_ROW "
                f"rank={rank} "
                f"state={row['state']} "
                f"strategy={row['strategy_code']} "
                f"symbol={row['symbol_group']} "
                f"side={row['side_code']} "
                f"candidate={row['candidate_code']} "
                f"pairs={row['pairs']} "
                f"sample_completion_pct={completion_pct:.2f} "
                f"net_expectancy={row['net_expectancy']} "
                f"placebo_pass={int(row['placebo_pass'] is True)} "
                f"placebo_delta_lower_bound={row['placebo_delta_lower_bound']} "
                f"paired_gain={row['paired_gain']} "
                f"paired_probability_positive="
                f"{row['paired_probability_positive']} "
                f"statistical_verdict={row['statistical_verdict']} "
                f"statistical_reason={row['statistical_reason']}"
            )

        counts = {}
        for row in visible:
            counts[row["state"]] = counts.get(row["state"], 0) + 1

        print(f"active_challengers={len(rows)}")
        print(
            "validation_candidates="
            f"{counts.get('VALIDATION_CANDIDATE', 0)}"
        )
        print(
            "early_baseline_superior_signals="
            f"{counts.get('EARLY_BASELINE_SUPERIOR_SIGNAL', 0)}"
        )
        print(
            "positive_but_baseline_inferior="
            f"{counts.get('POSITIVE_ABSOLUTE_BUT_BASELINE_INFERIOR', 0)}"
        )
        print(
            "insufficient_paired_evidence="
            f"{counts.get('INSUFFICIENT_PAIRED_EVIDENCE', 0)}"
        )

        print("paired_baseline_superiority_required=1")
        print("v2_rank_used_for_edge_strength=0")
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
            "ACTIVE_CHALLENGER_EVIDENCE_PRIORITY_V3_READY"
        )

        return 0

    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
