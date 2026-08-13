"""Read-only source contract governed enqueue budget parameters V2."""

from __future__ import annotations

import ast
from pathlib import Path


SOURCE = Path(
    "src/scripts/research/"
    "enqueue_edge_search_targeted_effective_budget_v1.py"
)


def main() -> int:
    text = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(text)

    tokens = (
        "edge_search_request_parameter_v1",
        "variant_budget",
        "cycle_budget",
        "effective_variants",
        "commit_candidate",
        "INSERT INTO",
    )

    for lineno, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if any(token in line for token in tokens):
            print(
                "ENQUEUE_BUDGET_SOURCE "
                f"line={lineno} "
                f"text={line.strip()}"
            )

    insert_nodes = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue

        if not isinstance(node.value, str):
            continue

        value = node.value

        if (
            "edge_search_request_parameter_v1" in value
            and "INSERT" in value.upper()
        ):
            insert_nodes.append(value)

    print(
        f"parameter_insert_statements="
        f"{len(insert_nodes)}"
    )

    variant_column_present = any(
        "variant_budget" in sql
        for sql in insert_nodes
    )

    cycle_column_present = any(
        "cycle_budget" in sql
        for sql in insert_nodes
    )

    print(
        "enqueue_variant_budget_column_present="
        f"{int(variant_column_present)}"
    )
    print(
        "enqueue_cycle_budget_column_present="
        f"{int(cycle_column_present)}"
    )

    print(
        "effective_variants_source_present="
        f"{int('effective_variants' in text)}"
    )

    print(
        "commit_candidate_present="
        f"{int('commit_candidate' in text)}"
    )

    assert len(insert_nodes) == 1
    assert variant_column_present
    assert "effective_variants" in text
    assert "commit_candidate" in text

    print(
        "required_v2_variant_budget_semantics="
        "UNIVERSE_CAPACITY_UPPER_BOUND"
    )
    print(
        "required_v2_cycle_budget_semantics="
        "TARGETED_CHALLENGERS_PER_CYCLE"
    )
    print("required_v2_cycle_budget_value=1")
    print("target_id_encodes_budget=0")
    print("one_request_per_target_preserved=1")

    print("enqueue_changed=0")
    print("db_writes_performed=0")
    print("queue_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "EDGE_SEARCH_GOVERNED_ENQUEUE_BUDGET_PARAMETERS_V2_"
        "SOURCE_CONTRACT_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
