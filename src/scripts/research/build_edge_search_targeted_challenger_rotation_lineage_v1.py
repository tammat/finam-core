"""Read-only forensic rotation lineage targeted EXIT_OOS."""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import RealDictCursor


SYMBOL = "BRQ6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
SIDE = "LONG"


def main() -> int:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Текущий frozen/promotion state.
            cur.execute(
                """
                SELECT
                    candidate_code,
                    workflow_stage,
                    statistical_verdict,
                    admission_id,
                    oos_run_id,
                    first_entered_at,
                    last_transition_at,
                    updated_at
                FROM analytics.entry_exit_promotion_workflow_v1
                WHERE strategy_code=%s
                  AND side_code=%s
                ORDER BY
                    first_entered_at NULLS LAST,
                    candidate_code
                """,
                (STRATEGY, SIDE),
            )
            workflow_rows = list(cur.fetchall())

            for row in workflow_rows:
                print(
                    "ROTATION_WORKFLOW_ROW "
                    f"candidate={row['candidate_code']} "
                    f"stage={row['workflow_stage']} "
                    f"verdict={row['statistical_verdict']} "
                    f"admission_id={row['admission_id'] or 'NONE'} "
                    f"oos_run_id={row['oos_run_id'] or 'NONE'} "
                    f"first_entered_at={row['first_entered_at']} "
                    f"last_transition_at={row['last_transition_at']}"
                )

            # Candidate universe реально присутствующий в shadow pairs.
            cur.execute(
                """
                SELECT
                    candidate_code,
                    count(*) AS pairs,
                    count(*) FILTER (WHERE is_oos) AS oos_pairs,
                    min(generated_at) AS first_generated_at,
                    max(generated_at) AS last_generated_at
                FROM analytics.entry_exit_signal_shadow_pair_v2
                WHERE symbol_code=%s
                  AND strategy_code=%s
                  AND side_code=%s
                GROUP BY candidate_code
                ORDER BY candidate_code
                """,
                (SYMBOL, STRATEGY, SIDE),
            )
            shadow_rows = list(cur.fetchall())

            shadow_codes = {
                str(row["candidate_code"])
                for row in shadow_rows
            }

            for row in shadow_rows:
                print(
                    "ROTATION_SHADOW_ROW "
                    f"candidate={row['candidate_code']} "
                    f"pairs={row['pairs']} "
                    f"oos_pairs={row['oos_pairs']} "
                    f"first_generated_at={row['first_generated_at']} "
                    f"last_generated_at={row['last_generated_at']}"
                )

            # Frozen hypotheses дают независимое evidence выбранных candidates.
            cur.execute(
                """
                SELECT
                    h.hypothesis_id,
                    h.lifecycle_state,
                    h.recommendation_code,
                    h.evidence,
                    h.created_at,
                    h.updated_at,
                    a.admission_id,
                    a.status_code AS admission_status,
                    a.reason_code AS admission_reason
                FROM analytics.trade_outcome_hypothesis_v1 h
                LEFT JOIN analytics.trade_outcome_oos_admission_v1 a
                  ON a.hypothesis_id=h.hypothesis_id
                WHERE h.symbol=%s
                  AND h.strategy_code=%s
                  AND h.side_code=%s
                  AND h.hypothesis_type='FILTER_OOS_CANDIDATE'
                ORDER BY h.created_at,h.hypothesis_id
                """,
                (SYMBOL, STRATEGY, SIDE),
            )
            hypothesis_rows = list(cur.fetchall())

            hypothesis_codes = set()

            for row in hypothesis_rows:
                evidence = row["evidence"] or {}
                code = evidence.get("candidate_code")

                if code:
                    hypothesis_codes.add(str(code))

                print(
                    "ROTATION_HYPOTHESIS_ROW "
                    f"candidate={code or 'NONE'} "
                    f"hypothesis_id={row['hypothesis_id']} "
                    f"lifecycle={row['lifecycle_state']} "
                    f"admission_status={row['admission_status'] or 'NONE'} "
                    f"admission_reason={row['admission_reason'] or 'NONE'}"
                )

            workflow_codes = {
                str(row["candidate_code"])
                for row in workflow_rows
            }

            observed_codes = (
                shadow_codes
                | workflow_codes
                | hypothesis_codes
            )

            frozen_codes = {
                str(row["candidate_code"])
                for row in workflow_rows
                if row["admission_id"] is not None
            }

            terminal_codes = {
                str(row["candidate_code"])
                for row in workflow_rows
                if str(row["workflow_stage"]).upper()
                in {
                    "REJECTED",
                    "ROLLED_BACK",
                }
            }

            print(f"workflow_candidates={len(workflow_codes)}")
            print(f"shadow_candidates={len(shadow_codes)}")
            print(f"hypothesis_candidates={len(hypothesis_codes)}")
            print(f"observed_candidate_codes={len(observed_codes)}")
            print(f"frozen_candidate_codes={len(frozen_codes)}")
            print(f"terminal_candidate_codes={len(terminal_codes)}")

            # Не утверждаем rotation, пока lineage её не доказывает.
            rotation_proven = (
                len(hypothesis_codes) > 1
                or len(frozen_codes) > 1
            )

            print(
                f"historical_rotation_observed="
                f"{int(rotation_proven)}"
            )

            print("universe_capacity_known=13")
            print("cycle_budget_known=1")
            print("automatic_rotation_assumed=0")
            print("allocator_changed=0")
            print("optimizer_changed=0")
            print("db_writes_performed=0")
            print("queue_writes_performed=0")
            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")

            print(
                "VERDICT="
                "EDGE_SEARCH_TARGETED_CHALLENGER_"
                "ROTATION_LINEAGE_V1_READY"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
