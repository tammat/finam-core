"""Read-only rollup governed targeted research productivity."""

from __future__ import annotations

import os
from collections import defaultdict
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor


ACTOR_ID = "system.targeted.budget.v1"


def scalar(cur, sql: str, params: tuple) -> int:
    cur.execute(sql, params)
    row = cur.fetchone()

    if row is None:
        return 0

    if len(row) != 1:
        raise RuntimeError(
            "PRODUCTIVITY_ROLLUP_SCALAR_EXPECTED_SINGLE_COLUMN"
        )

    return int(next(iter(row.values())) or 0)


def artifact_metrics(
    cur,
    *,
    symbol: str,
    strategy: str,
    side: str,
    started_at,
    finished_at,
) -> dict[str, int]:
    shadow_pairs = scalar(
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
        (
            symbol,
            strategy,
            side,
            started_at,
            finished_at,
        ),
    )

    candidates = scalar(
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
        (
            symbol,
            strategy,
            side,
            started_at,
            finished_at,
        ),
    )

    diagnostics = scalar(
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
        (
            started_at,
            finished_at,
            symbol,
            strategy,
            side,
        ),
    )

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
        (
            symbol,
            strategy,
            side,
            started_at,
            finished_at,
        ),
    )

    return {
        "candidates": candidates,
        "shadow_pairs": shadow_pairs,
        "diagnostics": diagnostics,
        "new_hypotheses": new_hypotheses,
    }


def main() -> int:
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
                    ep.variant_budget
                FROM marketcore_action.command_request_v2 q
                JOIN marketcore_action.research_process_v1 rp
                  ON rp.process_id=q.process_id
                JOIN marketcore_action.edge_search_request_parameter_v1 ep
                  ON ep.request_id=q.request_id
                WHERE q.actor_id=%s
                  AND q.status='COMPLETED'
                  AND rp.status_code='SUCCEEDED'
                  AND q.started_at IS NOT NULL
                  AND q.finished_at IS NOT NULL
                  AND q.target_id LIKE 'TARGETED_V1|%%'
                ORDER BY q.started_at
                """,
                (ACTOR_ID,),
            )

            runs = list(cur.fetchall())

            total_budget = 0
            total_candidates = 0
            total_pairs = 0
            total_diagnostics = 0
            total_hypotheses = 0
            total_runtime = Decimal("0")

            by_target = defaultdict(
                lambda: {
                    "runs": 0,
                    "budget": 0,
                    "candidates": 0,
                    "pairs": 0,
                    "diagnostics": 0,
                }
            )

            for run in runs:
                parts = str(run["target_id"]).split("|")

                if len(parts) != 5:
                    continue

                prefix, family, symbol, strategy, side = parts

                if prefix != "TARGETED_V1":
                    continue

                metrics = artifact_metrics(
                    cur,
                    symbol=symbol,
                    strategy=strategy,
                    side=side,
                    started_at=run["started_at"],
                    finished_at=run["finished_at"],
                )

                budget = int(run["variant_budget"])

                # Frozen targeted cycle может иметь ноль temporal rows;
                # не выдумываем candidate activity.
                candidates = metrics["candidates"]

                runtime = Decimal(
                    str(
                        (
                            run["finished_at"]
                            - run["started_at"]
                        ).total_seconds()
                    )
                )

                total_budget += budget
                total_candidates += candidates
                total_pairs += metrics["shadow_pairs"]
                total_diagnostics += metrics["diagnostics"]
                total_hypotheses += metrics["new_hypotheses"]
                total_runtime += runtime

                target_key = (
                    f"{family}|{symbol}|{strategy}|{side}"
                )

                bucket = by_target[target_key]
                bucket["runs"] += 1
                bucket["budget"] += budget
                bucket["candidates"] += candidates
                bucket["pairs"] += metrics["shadow_pairs"]
                bucket["diagnostics"] += metrics["diagnostics"]

                utilization = (
                    Decimal(candidates)
                    / Decimal(budget)
                    * Decimal("100")
                    if budget
                    else Decimal("0")
                )

                print(
                    "PRODUCTIVITY_RUN "
                    f"request_id={run['request_id']} "
                    f"target={target_key} "
                    f"variant_budget={budget} "
                    f"candidates={candidates} "
                    f"utilization_pct={utilization:.4f} "
                    f"shadow_pairs={metrics['shadow_pairs']} "
                    f"diagnostics={metrics['diagnostics']} "
                    f"new_hypotheses={metrics['new_hypotheses']} "
                    f"runtime_seconds={runtime}"
                )

            utilization_total = (
                Decimal(total_candidates)
                / Decimal(total_budget)
                * Decimal("100")
                if total_budget
                else Decimal("0")
            )

            direct_artifacts = (
                total_pairs
                + total_diagnostics
                + total_hypotheses
            )

            artifacts_per_candidate = (
                Decimal(direct_artifacts)
                / Decimal(total_candidates)
                if total_candidates
                else Decimal("0")
            )

            artifacts_per_budget = (
                Decimal(direct_artifacts)
                / Decimal(total_budget)
                if total_budget
                else Decimal("0")
            )

            print(
                "PRODUCTIVITY_ROLLUP "
                f"successful_runs={len(runs)} "
                f"allocated_budget={total_budget} "
                f"actual_candidates={total_candidates} "
                f"budget_utilization_pct={utilization_total:.4f} "
                f"shadow_pairs={total_pairs} "
                f"diagnostics={total_diagnostics} "
                f"new_hypotheses={total_hypotheses} "
                f"direct_artifacts={direct_artifacts} "
                f"runtime_seconds={total_runtime} "
                f"artifacts_per_candidate="
                f"{artifacts_per_candidate:.6f} "
                f"artifacts_per_budget_unit="
                f"{artifacts_per_budget:.6f}"
            )

            for target, bucket in sorted(by_target.items()):
                target_utilization = (
                    Decimal(bucket["candidates"])
                    / Decimal(bucket["budget"])
                    * Decimal("100")
                    if bucket["budget"]
                    else Decimal("0")
                )

                print(
                    "PRODUCTIVITY_TARGET_ROLLUP "
                    f"target={target} "
                    f"runs={bucket['runs']} "
                    f"budget={bucket['budget']} "
                    f"candidates={bucket['candidates']} "
                    f"utilization_pct={target_utilization:.4f} "
                    f"shadow_pairs={bucket['pairs']} "
                    f"diagnostics={bucket['diagnostics']}"
                )

    print("attribution_quality=TEMPORAL_TARGET_SCOPED")
    print("request_id_artifact_lineage_available=0")
    print("allocator_changed=0")
    print("db_writes_performed=0")
    print("queue_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "EDGE_SEARCH_RESEARCH_BUDGET_PRODUCTIVITY_ROLLUP_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
