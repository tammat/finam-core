"""Governed enqueue текущего targeted Edge Search allocation.

По умолчанию read-only shadow.
Реальная запись разрешается только через --commit.
"""

from __future__ import annotations

import argparse
import os
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor

from scripts.research.build_edge_search_research_budget_allocation_shadow_v1 import (
    build_allocations,
)
from marketcore.services.research.edge_search_target_descriptor_resolver_v1 import (
    resolve_target_descriptor_v1,
)
from marketcore.services.research.edge_search_variant_capacity_resolver_v1 import (
    resolve_variant_capacity_v1,
)
from marketcore.services.research.edge_search_governed_enqueue_guard_v1 import (
    evaluate_governed_enqueue_v1,
)
from marketcore.services.research.targeted_research_executor_mapping_v1 import (
    resolve_targeted_research_executor_v1,
)


def build_candidates(conn):
    _decisions, _eligible, allocations, _total_weight = build_allocations()

    candidates = []

    for item, weight, requested_variants in allocations:
        descriptor = resolve_target_descriptor_v1(
            conn,
            symbol=item.symbol,
            research_family=item.research_family,
        )

        if descriptor.state != "RESOLVED":
            print(
                "GOVERNED_ENQUEUE_SKIP "
                f"symbol={item.symbol} "
                f"family={item.research_family} "
                f"reason=UNRESOLVED_DESCRIPTOR "
                f"descriptor_reason={descriptor.reason}"
            )
            continue

        capacity = resolve_variant_capacity_v1(
            symbol=item.symbol,
            research_family=item.research_family,
            strategy=descriptor.strategy,
            side=descriptor.side,
            requested_variants=int(requested_variants),
        )

        if capacity.effective_variants <= 0:
            print(
                "GOVERNED_ENQUEUE_SKIP "
                f"symbol={item.symbol} "
                f"family={item.research_family} "
                f"reason=ZERO_EFFECTIVE_CAPACITY"
            )
            continue

        mapping = resolve_targeted_research_executor_v1(
            item.research_family
        )

        executable = (
            mapping.executor_code is not None
            and mapping.handler is not None
            and mapping.state_code == "REUSE_EXISTING_EXECUTOR"
        )

        if not executable:
            print(
                "GOVERNED_ENQUEUE_SKIP "
                f"symbol={item.symbol} "
                f"family={item.research_family} "
                f"reason=NO_EXECUTABLE_MAPPING"
            )
            continue

        target_id = (
            "TARGETED_V1|"
            f"{item.research_family}|"
            f"{item.symbol}|"
            f"{descriptor.strategy}|"
            f"{descriptor.side}"
        )

        candidates.append(
            {
                "symbol": item.symbol,
                "family": item.research_family,
                "strategy": descriptor.strategy,
                "side": descriptor.side,
                "priority": item.priority,
                "weight": int(weight),
                "requested_variants": int(requested_variants),
                "effective_variants": int(
                    capacity.effective_variants
                ),
                "cycle_budget": 1,
                "released_variants": int(
                    capacity.unused_variants
                ),
                "executor": mapping.executor_code,
                "target_id": target_id,
            }
        )

    return candidates


def commit_candidate(conn, candidate):
    target_id = candidate["target_id"]

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Сериализация enqueue для одного logical target.
        cur.execute(
            "SELECT pg_advisory_xact_lock(hashtext(%s))",
            (target_id,),
        )

        # Повторная проверка под lock.
        cur.execute(
            """
            SELECT request_id,status
            FROM marketcore_action.command_request_v2
            WHERE target_id=%s
              AND status IN ('PENDING','RUNNING')
            ORDER BY requested_at DESC
            """,
            (target_id,),
        )

        active = list(cur.fetchall())

        if active:
            return {
                "written": False,
                "reason": "ALREADY_ACTIVE",
                "request_id": str(active[0]["request_id"]),
            }

        request_id = str(uuid.uuid4())

        cur.execute(
            """
            INSERT INTO marketcore_action.command_request_v2 (
                request_id,
                action_id,
                request_kind,
                command_code,
                actor_id,
                target_id,
                status,
                requested_at
            )
            VALUES (
                %s,
                'research.edge_search.run',
                'EDGE_SEARCH_RUN',
                'RESEARCH.RUN_EDGE_SEARCH',
                'system.targeted.budget.v1',
                %s,
                'PENDING',
                clock_timestamp()
            )
            """,
            (
                request_id,
                target_id,
            ),
        )

        cur.execute(
            """
            INSERT INTO marketcore_action.edge_search_request_parameter_v1 (
                request_id,
                variant_budget,
                cycle_budget
            )
            VALUES (%s,%s,%s)
            """,
            (
                request_id,
                candidate["effective_variants"],
                candidate["cycle_budget"],
            ),
        )

        return {
            "written": True,
            "reason": "ENQUEUED",
            "request_id": request_id,
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Разрешить атомарную запись governed request.",
    )
    args = parser.parse_args()

    writes = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        candidates = build_candidates(conn)

        for candidate in candidates:
            guard = evaluate_governed_enqueue_v1(
                conn,
                target_id=candidate["target_id"],
            )

            print(
                "GOVERNED_ENQUEUE_CANDIDATE "
                f"symbol={candidate['symbol']} "
                f"family={candidate['family']} "
                f"strategy={candidate['strategy']} "
                f"side={candidate['side']} "
                f"requested_variants={candidate['requested_variants']} "
                f"effective_variants={candidate['effective_variants']} "
                f"cycle_budget={candidate['cycle_budget']} "
                f"released_variants={candidate['released_variants']} "
                f"executor={candidate['executor']} "
                f"target_id={candidate['target_id']} "
                f"guard_decision={guard.decision} "
                f"guard_reason={guard.reason}"
            )

            if not args.commit:
                continue

            if guard.decision != "ADMIT_SHADOW":
                print(
                    "GOVERNED_ENQUEUE_RESULT "
                    f"target_id={candidate['target_id']} "
                    f"written=0 "
                    f"reason={guard.reason}"
                )
                continue

            result = commit_candidate(
                conn,
                candidate,
            )

            if result["written"]:
                writes += 1

            print(
                "GOVERNED_ENQUEUE_RESULT "
                f"target_id={candidate['target_id']} "
                f"request_id={result['request_id']} "
                f"written={int(result['written'])} "
                f"reason={result['reason']} "
                f"variant_budget={candidate['effective_variants']} "
                f"cycle_budget={candidate['cycle_budget']}"
            )

        if args.commit:
            conn.commit()
        else:
            conn.rollback()

    print(f"candidate_count={len(candidates)}")
    print(f"queue_writes_performed={writes}")
    print(f"commit_enabled={int(args.commit)}")
    print("target_identity_encodes_budget=0")
    print("one_request_per_allocation_target=1")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "EDGE_SEARCH_TARGETED_GOVERNED_ENQUEUE_EFFECTIVE_BUDGET_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
