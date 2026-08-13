"""Read-only shadow модели capacity vs фактического consumption."""

from __future__ import annotations

import os
from collections import defaultdict
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor


ACTOR_ID = "system.targeted.budget.v1"
MIN_RUNS_FOR_POLICY = 3


def scalar(cur, sql: str, params: tuple) -> int:
    cur.execute(sql, params)
    row = cur.fetchone()

    if row is None:
        return 0

    if len(row) != 1:
        raise RuntimeError(
            "CAPACITY_CONSUMPTION_SCALAR_EXPECTED_SINGLE_COLUMN"
        )

    return int(next(iter(row.values())) or 0)


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
                  AND q.target_id LIKE 'TARGETED_V1|%%'
                  AND q.started_at IS NOT NULL
                  AND q.finished_at IS NOT NULL
                ORDER BY q.started_at
                """,
                (ACTOR_ID,),
            )

            runs = list(cur.fetchall())

            targets = defaultdict(
                lambda: {
                    "runs": 0,
                    "capacity": 0,
                    "consumed": 0,
                }
            )

            for run in runs:
                parts = str(run["target_id"]).split("|")

                if len(parts) != 5:
                    continue

                prefix, family, symbol, strategy, side = parts

                if prefix != "TARGETED_V1":
                    continue

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
                        run["started_at"],
                        run["finished_at"],
                    ),
                )

                capacity = int(run["variant_budget"])
                consumed = candidates
                remaining = max(capacity - consumed, 0)

                target = (
                    f"{family}|{symbol}|{strategy}|{side}"
                )

                bucket = targets[target]
                bucket["runs"] += 1
                bucket["capacity"] += capacity
                bucket["consumed"] += consumed

                utilization = (
                    Decimal(consumed)
                    / Decimal(capacity)
                    * Decimal("100")
                    if capacity
                    else Decimal("0")
                )

                print(
                    "CAPACITY_CONSUMPTION_RUN "
                    f"request_id={run['request_id']} "
                    f"target={target} "
                    f"capacity_budget={capacity} "
                    f"cycle_consumption={consumed} "
                    f"remaining_capacity={remaining} "
                    f"utilization_pct={utilization:.4f}"
                )

            for target, bucket in sorted(targets.items()):
                runs_count = bucket["runs"]
                capacity = bucket["capacity"]
                consumed = bucket["consumed"]
                remaining = max(capacity - consumed, 0)

                utilization = (
                    Decimal(consumed)
                    / Decimal(capacity)
                    * Decimal("100")
                    if capacity
                    else Decimal("0")
                )

                average_consumption = (
                    Decimal(consumed)
                    / Decimal(runs_count)
                    if runs_count
                    else Decimal("0")
                )

                policy_ready = (
                    runs_count >= MIN_RUNS_FOR_POLICY
                )

                print(
                    "CAPACITY_CONSUMPTION_TARGET "
                    f"target={target} "
                    f"successful_runs={runs_count} "
                    f"allocated_capacity={capacity} "
                    f"actual_consumption={consumed} "
                    f"remaining_capacity={remaining} "
                    f"utilization_pct={utilization:.4f} "
                    f"avg_candidates_per_cycle="
                    f"{average_consumption:.4f} "
                    f"policy_sample_ready={int(policy_ready)}"
                )

            total_runs = sum(
                item["runs"]
                for item in targets.values()
            )

            policy_ready = (
                total_runs >= MIN_RUNS_FOR_POLICY
            )

            print(f"successful_runs={total_runs}")
            print(
                f"minimum_runs_for_policy="
                f"{MIN_RUNS_FOR_POLICY}"
            )
            print(
                f"capacity_policy_change_allowed="
                f"{int(policy_ready)}"
            )

            print("allocator_changed=0")
            print("budget_transport_changed=0")
            print("db_writes_performed=0")
            print("queue_writes_performed=0")
            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")

            print(
                "VERDICT="
                "EDGE_SEARCH_RESEARCH_BUDGET_"
                "CAPACITY_CONSUMPTION_MODEL_SHADOW_V1_READY"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
