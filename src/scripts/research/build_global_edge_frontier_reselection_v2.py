from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor


ZERO = Decimal("0")


def dec(value) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def gap_to_positive(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("999999")
    return max(ZERO, -value)


def frontier_state(
    net_expectancy: Decimal | None,
    paired_gain: Decimal | None,
    placebo_lower_bound: Decimal | None,
) -> str:
    if paired_gain is None:
        return "PAIRED_EVIDENCE_MISSING"

    if (
        net_expectancy is not None
        and net_expectancy > 0
        and paired_gain > 0
        and placebo_lower_bound is not None
        and placebo_lower_bound > 0
    ):
        return "TARGET_CANDIDATE"

    if (
        net_expectancy is not None
        and net_expectancy > 0
        and paired_gain > 0
    ):
        return "PLACEBO_INFERIOR"

    if (
        net_expectancy is not None
        and net_expectancy > 0
        and paired_gain <= 0
    ):
        return "NET_POSITIVE_BASELINE_INFERIOR"

    if (
        net_expectancy is not None
        and net_expectancy <= 0
        and paired_gain > 0
    ):
        return "BASELINE_SUPERIOR_NET_NEGATIVE"

    return "NET_NEGATIVE_BASELINE_INFERIOR"


def main() -> int:
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    r.strategy_code,
                    r.symbol_group,
                    r.side_code,
                    r.candidate_code,
                    r.pairs,
                    r.oos_pairs,

                    (r.metrics #>>
                        '{economics_decomposition,net_expectancy_r}')::numeric
                        AS net_expectancy,

                    (r.metrics #>>
                        '{statistical_gate,paired_expectancy_gain_r}')::numeric
                        AS paired_gain,

                    (r.metrics #>>
                        '{statistical_gate,probability_positive}')::numeric
                        AS probability_positive,

                    (r.metrics #>>
                        '{negative_control,delta_lower_bound_r}')::numeric
                        AS placebo_delta_lower_bound,

                    (r.metrics #>>
                        '{negative_control,passed}')::boolean
                        AS placebo_pass,

                    w.statistical_verdict,
                    w.expensive_gates_pass

                FROM analytics.entry_exit_recommendation_v1 r

                JOIN analytics.entry_exit_promotion_workflow_v1 w
                  ON w.strategy_code=r.strategy_code
                 AND w.symbol_group=r.symbol_group
                 AND w.side_code=r.side_code
                 AND w.candidate_code=r.candidate_code

                WHERE w.evidence #>>
                    '{promotion_workflow,selected_for_shadow_funnel}'
                    = 'true'
                """
            )

            rows = []

            for row in cur.fetchall():
                net = dec(row["net_expectancy"])
                gain = dec(row["paired_gain"])
                placebo_lb = dec(row["placebo_delta_lower_bound"])

                state = frontier_state(
                    net,
                    gain,
                    placebo_lb,
                )

                frontier_gap = (
                    gap_to_positive(net)
                    + gap_to_positive(gain)
                    + gap_to_positive(placebo_lb)
                )

                pairs = int(row["pairs"] or 0)

                sample_penalty = (
                    max(Decimal("0"), Decimal("60") - Decimal(pairs))
                    / Decimal("60")
                )

                priority_gap = frontier_gap + sample_penalty

                rows.append(
                    {
                        **row,
                        "net_expectancy": net,
                        "paired_gain": gain,
                        "placebo_delta_lower_bound": placebo_lb,
                        "frontier_state": state,
                        "frontier_gap": frontier_gap,
                        "sample_penalty": sample_penalty,
                        "priority_gap": priority_gap,
                    }
                )

        state_order = {
            "TARGET_CANDIDATE": 0,
            "PLACEBO_INFERIOR": 1,
            "NET_POSITIVE_BASELINE_INFERIOR": 2,
            "BASELINE_SUPERIOR_NET_NEGATIVE": 3,
            "PAIRED_EVIDENCE_MISSING": 4,
            "NET_NEGATIVE_BASELINE_INFERIOR": 5,
        }

        rows.sort(
            key=lambda row: (
                state_order[row["frontier_state"]],
                row["priority_gap"],
                -int(row["pairs"] or 0),
                row["strategy_code"],
                row["symbol_group"],
                row["candidate_code"],
            )
        )

        for rank, row in enumerate(rows, start=1):
            print(
                "FRONTIER_V2_ROW "
                f"rank={rank} "
                f"state={row['frontier_state']} "
                f"strategy={row['strategy_code']} "
                f"symbol_group={row['symbol_group']} "
                f"side={row['side_code']} "
                f"candidate={row['candidate_code']} "
                f"pairs={row['pairs']} "
                f"oos_pairs={row['oos_pairs']} "
                f"net_expectancy={row['net_expectancy']} "
                f"paired_gain={row['paired_gain']} "
                f"placebo_delta_lower_bound="
                f"{row['placebo_delta_lower_bound']} "
                f"probability_positive="
                f"{row['probability_positive']} "
                f"frontier_gap={row['frontier_gap']} "
                f"sample_penalty={row['sample_penalty']} "
                f"priority_gap={row['priority_gap']} "
                f"statistical_verdict="
                f"{row['statistical_verdict']} "
                f"expensive_pass="
                f"{int(bool(row['expensive_gates_pass']))}"
            )

        target_candidates = sum(
            row["frontier_state"] == "TARGET_CANDIDATE"
            for row in rows
        )

        print(f"active_challengers={len(rows)}")
        print(f"target_candidates={target_candidates}")
        print("ranking_dimensions=net,paired_gain,placebo,sample_maturity")

        # V2 пока является безопасным read-model.
        # Physical-contract segmentation добавим отдельным доказанным
        # источником, а не будем угадывать contract из symbol_group.
        print("physical_contract_segmentation_required=1")
        print("physical_contract_segmentation_materialized=0")

        print("db_writes_performed=0")
        print("production_pipeline_changed=0")
        print("thresholds_changed=0")
        print("net_first_logic_changed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        print(
            "VERDICT="
            "GLOBAL_EDGE_FRONTIER_RESELECTION_V2_READY"
        )

        return 0

    finally:
        conn.rollback()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
