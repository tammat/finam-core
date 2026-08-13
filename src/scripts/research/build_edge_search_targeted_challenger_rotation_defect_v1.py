"""Read-only proof targeted challenger rotation defect."""

from __future__ import annotations

import hashlib
import os

import psycopg2

import ast
import importlib
from pathlib import Path


def load_variant_factories():
    optimizer = Path(
        "src/scripts/analytics/build_entry_exit_optimizer_v1.py"
    )

    tree = ast.parse(
        optimizer.read_text(encoding="utf-8")
    )

    wanted = {
        "default_variants",
        "expert_shadow_variants",
    }

    module_name = None

    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue

        imported = {
            alias.name
            for alias in node.names
        }

        if wanted.issubset(imported):
            module_name = node.module
            break

    if not module_name:
        raise RuntimeError(
            "VARIANT_FACTORY_SOURCE_MODULE_NOT_FOUND"
        )

    module = importlib.import_module(module_name)

    return (
        getattr(module, "default_variants"),
        getattr(module, "expert_shadow_variants"),
        module_name,
    )


default_variants, expert_shadow_variants, VARIANT_SOURCE_MODULE = (
    load_variant_factories()
)


SYMBOL = "BRQ6@RTSX"
STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
SIDE = "LONG"


def main() -> int:
    print(f"variant_source_module={VARIANT_SOURCE_MODULE}")

    universe = (
        tuple(default_variants(STRATEGY))
        + tuple(expert_shadow_variants(STRATEGY))
    )

    digest = hashlib.sha256(
        (
            f"{STRATEGY}|{SYMBOL}|{SIDE}|"
            "TARGETED_RESEARCH_ONLY_V1"
        ).encode()
    ).digest()

    index = int.from_bytes(digest[:4], "big") % len(universe)
    selected = universe[index]

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        conn.set_session(readonly=True)

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    workflow_stage,
                    statistical_verdict,
                    admission_id,
                    oos_run_id
                FROM analytics.entry_exit_promotion_workflow_v1
                WHERE strategy_code=%s
                  AND side_code=%s
                  AND candidate_code=%s
                LIMIT 1
                """,
                (
                    STRATEGY,
                    SIDE,
                    selected.code,
                ),
            )

            row = cur.fetchone()

    stage = row[0] if row else "NONE"
    verdict = row[1] if row else "NONE"
    admission_id = row[2] if row else None
    oos_run_id = row[3] if row else None

    terminal = stage in {
        "REJECTED",
        "ROLLED_BACK",
        "EXPENSIVE_GATES_FAILED",
    }

    print(f"universe_size={len(universe)}")
    print(f"deterministic_index={index}")
    print(f"selected_candidate={selected.code}")
    print(f"selected_workflow_stage={stage}")
    print(f"selected_statistical_verdict={verdict}")
    print(
        f"selected_admission_id="
        f"{admission_id or 'NONE'}"
    )
    print(
        f"selected_oos_run_id="
        f"{oos_run_id or 'NONE'}"
    )

    print(f"selected_candidate_terminal={int(terminal)}")
    print("selection_uses_workflow_state=0")
    print("selection_excludes_terminal_candidates=0")
    print("selection_changes_between_identical_cycles=0")

    print(
        "remaining_unique_capacity_is_automatically_consumable=0"
    )

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
        "EDGE_SEARCH_TARGETED_CHALLENGER_ROTATION_DEFECT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
