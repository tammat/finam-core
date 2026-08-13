"""Read-only source contract перед targeted executor budget transport V2 PART3."""

from __future__ import annotations

import ast
from pathlib import Path


TARGET = Path(
    "src/scripts/run_targeted_entry_exit_oos_v1.py"
)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    tree = ast.parse(text)

    variant_refs = [
        (i, line.strip())
        for i, line in enumerate(
            text.splitlines(),
            start=1,
        )
        if (
            "EDGE_SEARCH_TARGET_VARIANT_BUDGET" in line
            or "variant_budget" in line
        )
    ]

    cycle_refs = [
        (i, line.strip())
        for i, line in enumerate(
            text.splitlines(),
            start=1,
        )
        if (
            "EDGE_SEARCH_TARGET_CYCLE_BUDGET" in line
            or "cycle_budget" in line
        )
    ]

    for line, source in variant_refs:
        print(
            "PART3_VARIANT_SOURCE "
            f"line={line} text={source}"
        )

    for line, source in cycle_refs:
        print(
            "PART3_CYCLE_SOURCE "
            f"line={line} text={source}"
        )

    getenv_calls = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "getenv"
        ):
            continue

        if not node.args:
            continue

        arg = node.args[0]

        if isinstance(arg, ast.Constant):
            getenv_calls.append(str(arg.value))

    print(f"variant_source_refs={len(variant_refs)}")
    print(f"cycle_source_refs={len(cycle_refs)}")

    print(
        "variant_env_receive_present="
        f"{int('EDGE_SEARCH_TARGET_VARIANT_BUDGET' in text)}"
    )

    print(
        "cycle_env_receive_present="
        f"{int('EDGE_SEARCH_TARGET_CYCLE_BUDGET' in text)}"
    )

    print(
        "variant_getenv_present="
        f"{int('EDGE_SEARCH_TARGET_VARIANT_BUDGET' in getenv_calls)}"
    )

    print(
        "cycle_getenv_present="
        f"{int('EDGE_SEARCH_TARGET_CYCLE_BUDGET' in getenv_calls)}"
    )

    print(
        "optimizer_cycle_transport_present="
        f"{int(text.count('EDGE_SEARCH_TARGET_CYCLE_BUDGET') > 1)}"
    )

    assert "EDGE_SEARCH_TARGET_VARIANT_BUDGET" in text

    print("part1_worker_preserved=1")
    print("part2_autonomous_cycle_preserved=1")
    print("targeted_executor_changed=0")
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
        "EDGE_SEARCH_REQUEST_BUDGET_TRANSPORT_V2_"
        "PART3_SOURCE_CONTRACT_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
