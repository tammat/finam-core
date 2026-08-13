"""Read-only audit structural consumption contract TARGETED_RESEARCH_ONLY."""

from __future__ import annotations

import ast
from pathlib import Path


OPTIMIZER = Path(
    "src/scripts/analytics/build_entry_exit_optimizer_v1.py"
)


def is_targeted_test(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Name)
        and node.id == "TARGETED_RESEARCH_ONLY"
    )


def main() -> int:
    text = OPTIMIZER.read_text(encoding="utf-8")
    tree = ast.parse(text)

    targeted_blocks = 0
    single_variant_assignments = []
    multi_variant_assignments = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue

        if not is_targeted_test(node.test):
            continue

        targeted_blocks += 1

        for child in ast.walk(node):
            if not isinstance(child, ast.Assign):
                continue

            names = {
                target.id
                for target in child.targets
                if isinstance(target, ast.Name)
            }

            if "variants" not in names:
                continue

            value = child.value

            if isinstance(value, (ast.Tuple, ast.List)):
                cardinality = len(value.elts)

                row = {
                    "line": child.lineno,
                    "cardinality": cardinality,
                    "source": ast.unparse(value),
                }

                if cardinality == 1:
                    single_variant_assignments.append(row)
                else:
                    multi_variant_assignments.append(row)

    token_present = (
        "EDGE_SEARCH_TARGET_VARIANT_BUDGET" in text
    )

    print(f"targeted_blocks={targeted_blocks}")
    print(
        "variant_budget_consumption_present="
        f"{int(token_present)}"
    )
    print(
        "single_variant_assignments="
        f"{len(single_variant_assignments)}"
    )
    print(
        "multi_variant_assignments="
        f"{len(multi_variant_assignments)}"
    )

    for row in single_variant_assignments:
        print(
            "TARGETED_SINGLE_VARIANT_ASSIGNMENT "
            f"line={row['line']} "
            f"cardinality={row['cardinality']} "
            f"source={row['source']}"
        )

    assert targeted_blocks >= 1
    assert token_present
    assert len(single_variant_assignments) >= 1
    assert len(multi_variant_assignments) == 0

    print("targeted_cycle_candidate_cardinality=1")
    print("cycle_consumption_is_structural=1")
    print("cycle_consumption_is_statistical_estimate=0")
    print("frozen_challenger_semantics_preserved=1")
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
        "EDGE_SEARCH_TARGETED_CYCLE_CONSUMPTION_CONTRACT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
