"""Read-only productivity attribution для governed targeted research run."""

from __future__ import annotations

import argparse
import os

import psycopg2
from psycopg2.extras import RealDictCursor


def scalar(cur, sql: str, params: tuple) -> int:
    """Возвращает единственное scalar-значение из RealDictCursor."""
    cur.execute(sql, params)
    row = cur.fetchone()

    if row is None:
        return 0

    if len(row) != 1:
        raise RuntimeError(
            "PRODUCTIVITY_SCALAR_EXPECTED_SINGLE_COLUMN"
        )

    value = next(iter(row.values()))
    return int(value or 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-id", required=True)
    args = parser.parse_args()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    q.request_id,
                    q.target_id,
                    q.started_at,
                    q.finished_at,
                    q.status,
                    rp.status_code AS process_status,
                    ep.variant_budget
                FROM marketcore_action.command_request_v2 q
                JOIN marketcore_action.research_process_v1 rp
                  ON rp.process_id=q.process_id
                JOIN marketcore_action.edge_search_request_parameter_v1 ep
                  ON ep.request_id=q.request_id
                WHERE q.request_id=%s
                """,
                (args.request_id,),
            )
            run = cur.fetchone()

            if not run:
                raise RuntimeError("PRODUCTIVITY_REQUEST_NOT_FOUND")

            if (
                run["status"] != "COMPLETED"
                or run["process_status"] != "SUCCEEDED"
                or not run["started_at"]
                or not run["finished_at"]
            ):
                raise RuntimeError(
                    "PRODUCTIVITY_REQUIRES_SUCCESSFUL_TERMINAL_RUN"
                )

            parts = str(run["target_id"]).split("|")

            if len(parts) != 5 or parts[0] != "TARGETED_V1":
                raise RuntimeError("PRODUCTIVITY_TARGET_ID_INVALID")

            _, family, symbol, strategy, side = parts
            started = run["started_at"]
            finished = run["finished_at"]
            budget = int(run["variant_budget"])

            # Точные target-scoped новые/обновлённые hypothesis rows.
            new_hypotheses = scalar(
                cur,
                """
                SELECT count(*)
                FROM analytics.trade_outcome_hypothesis_v1
                WHERE symbol=%s
                  AND strategy_code=%s
                  AND side_code=%s
                  AND created_at >= %s
                  AND created_at <= %s
                """,
                (symbol, strategy, side, started, finished),
            )

            touched_hypotheses = scalar(
                cur,
                """
                SELECT count(*)
                FROM analytics.trade_outcome_hypothesis_v1
                WHERE symbol=%s
                  AND strategy_code=%s
                  AND side_code=%s
                  AND updated_at >= %s
                  AND updated_at <= %s
                """,
                (symbol, strategy, side, started, finished),
            )

            # Admission можно точно привязать через hypothesis.
            new_oos_admissions = scalar(
                cur,
                """
                SELECT count(*)
                FROM analytics.trade_outcome_oos_admission_v1 a
                JOIN analytics.trade_outcome_hypothesis_v1 h
                  ON h.hypothesis_id=a.hypothesis_id
                WHERE h.symbol=%s
                  AND h.strategy_code=%s
                  AND h.side_code=%s
                  AND a.created_at >= %s
                  AND a.created_at <= %s
                """,
                (symbol, strategy, side, started, finished),
            )

            touched_oos_admissions = scalar(
                cur,
                """
                SELECT count(*)
                FROM analytics.trade_outcome_oos_admission_v1 a
                JOIN analytics.trade_outcome_hypothesis_v1 h
                  ON h.hypothesis_id=a.hypothesis_id
                WHERE h.symbol=%s
                  AND h.strategy_code=%s
                  AND h.side_code=%s
                  AND a.updated_at >= %s
                  AND a.updated_at <= %s
                """,
                (symbol, strategy, side, started, finished),
            )

            # UPSERT artifacts: это touched, а не доказанно "new".
            shadow_pairs_touched = scalar(
                cur,
                """
                SELECT count(*)
                FROM analytics.entry_exit_signal_shadow_pair_v2
                WHERE symbol_code=%s
                  AND strategy_code=%s
                  AND side_code=%s
                  AND generated_at >= %s
                  AND generated_at <= %s
                """,
                (symbol, strategy, side, started, finished),
            )

            candidates_touched = scalar(
                cur,
                """
                SELECT count(DISTINCT candidate_code)
                FROM analytics.entry_exit_signal_shadow_pair_v2
                WHERE symbol_code=%s
                  AND strategy_code=%s
                  AND side_code=%s
                  AND generated_at >= %s
                  AND generated_at <= %s
                """,
                (symbol, strategy, side, started, finished),
            )

            diagnostics_touched = scalar(
                cur,
                """
                SELECT count(*)
                FROM analytics.entry_exit_shadow_diagnostic_v1 d
                WHERE d.generated_at >= %s
                  AND d.generated_at <= %s
                  AND EXISTS (
                      SELECT 1
                      FROM analytics.entry_exit_signal_shadow_pair_v2 p
                      WHERE p.source_signal_id=d.source_signal_id
                        AND p.candidate_code=d.candidate_code
                        AND p.symbol_code=%s
                        AND p.strategy_code=%s
                        AND p.side_code=%s
                  )
                """,
                (started, finished, symbol, strategy, side),
            )

            # Эти таблицы не имеют request_id/symbol exact linkage.
            # Считаем только temporal strategy/side touches.
            promotion_workflow_touched = scalar(
                cur,
                """
                SELECT count(*)
                FROM analytics.entry_exit_promotion_workflow_v1
                WHERE strategy_code=%s
                  AND side_code=%s
                  AND updated_at >= %s
                  AND updated_at <= %s
                """,
                (strategy, side, started, finished),
            )

            family_evidence_touched = scalar(
                cur,
                """
                SELECT count(*)
                FROM analytics.entry_exit_family_evidence_v1
                WHERE side_code=%s
                  AND generated_at >= %s
                  AND generated_at <= %s
                """,
                (side, started, finished),
            )

            runtime_seconds = (
                finished - started
            ).total_seconds()

            actual_candidates = max(candidates_touched, 1)
            budget_utilization = (
                actual_candidates / budget * 100.0
                if budget > 0
                else 0.0
            )

            direct_artifacts = (
                new_hypotheses
                + new_oos_admissions
                + shadow_pairs_touched
                + diagnostics_touched
            )

            artifacts_per_candidate = (
                direct_artifacts / actual_candidates
                if actual_candidates
                else 0.0
            )

            artifacts_per_budget = (
                direct_artifacts / budget
                if budget
                else 0.0
            )

            print(
                "RESEARCH_PRODUCTIVITY "
                f"request_id={run['request_id']} "
                f"symbol={symbol} "
                f"family={family} "
                f"strategy={strategy} "
                f"side={side} "
                f"variant_budget={budget} "
                f"actual_candidates_evaluated={actual_candidates} "
                f"candidate_budget_utilization_pct={budget_utilization:.4f} "
                f"runtime_seconds={runtime_seconds:.6f}"
            )

            print(
                "PRODUCTIVITY_ARTIFACTS "
                f"new_hypotheses={new_hypotheses} "
                f"touched_hypotheses={touched_hypotheses} "
                f"new_oos_admissions={new_oos_admissions} "
                f"touched_oos_admissions={touched_oos_admissions} "
                f"shadow_pairs_touched={shadow_pairs_touched} "
                f"diagnostics_touched={diagnostics_touched} "
                f"promotion_workflow_touched={promotion_workflow_touched} "
                f"family_evidence_touched={family_evidence_touched}"
            )

            print(f"direct_artifacts={direct_artifacts}")
            print(
                f"artifacts_per_candidate="
                f"{artifacts_per_candidate:.6f}"
            )
            print(
                f"artifacts_per_allocated_budget_unit="
                f"{artifacts_per_budget:.6f}"
            )

            print(
                "attribution_quality="
                "TEMPORAL_TARGET_SCOPED"
            )
            print(
                "request_id_artifact_lineage_available=0"
            )
            print(
                "upsert_rows_counted_as_touched_not_new=1"
            )
            print("db_writes_performed=0")
            print("queue_writes_performed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")
            print(
                "VERDICT="
                "EDGE_SEARCH_RESEARCH_BUDGET_PRODUCTIVITY_SHADOW_V1_READY"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
