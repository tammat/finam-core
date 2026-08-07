#!/usr/bin/env python3
from __future__ import annotations

import ast
import pathlib


ROOT = pathlib.Path("/opt/finam-core")
ADAPTER = (
    ROOT
    / "src/finam_core/research/"
    "postgresql_edge_backtest_adapter_v1.py"
)

TARGET_STRATEGY = "RSI_MEAN_REVERSION_V1"


def main() -> int:
    if not ADAPTER.is_file():
        raise SystemExit(f"ERROR=adapter_missing:{ADAPTER}")

    source = ADAPTER.read_text(
        encoding="utf-8",
        errors="replace",
    )
    lines = source.splitlines()
    tree = ast.parse(source, filename=str(ADAPTER))

    function_rows: list[tuple[str, int, int]] = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        name_lower = node.name.lower()

        if "rsi" in name_lower or "mean_reversion" in name_lower:
            function_rows.append(
                (
                    node.name,
                    node.lineno,
                    getattr(node, "end_lineno", node.lineno),
                )
            )

    marker_lines = [
        index
        for index, line in enumerate(lines, start=1)
        if TARGET_STRATEGY in line
    ]

    supported_block = "\n".join(lines[20:55])
    registry_block = "\n".join(lines[550:610])

    supported_contains_rsi = (
        TARGET_STRATEGY in supported_block
    )
    registry_contains_rsi = (
        TARGET_STRATEGY in registry_block
    )

    print("=== POSTGRESQL EDGE BACKTEST RSI DISPATCH AUDIT V1 ===")
    print(f"adapter_file={ADAPTER}")
    print(
        f"rsi_strategy_marker_count="
        f"{len(marker_lines)}"
    )
    print(
        f"supported_strategy_contains_rsi="
        f"{int(supported_contains_rsi)}"
    )
    print(
        f"signal_registry_contains_rsi="
        f"{int(registry_contains_rsi)}"
    )
    print(
        f"rsi_candidate_function_count="
        f"{len(function_rows)}"
    )

    for line_number in marker_lines:
        print(
            "RSI_MARKER "
            f"line={line_number} "
            f"text={lines[line_number - 1].strip()!r}"
        )

    for name, start, end in sorted(function_rows):
        print(
            "RSI_FUNCTION_CANDIDATE "
            f"name={name} "
            f"start_line={start} "
            f"end_line={end}"
        )

        for line_number in range(start, end + 1):
            print(
                "RSI_FUNCTION_SOURCE "
                f"line={line_number} "
                f"text={lines[line_number - 1]!r}"
            )

    print("=== SUPPORTED_STRATEGIES_BLOCK ===")

    for line_number in range(21, 56):
        if line_number <= len(lines):
            print(
                f"{line_number:05d}: "
                f"{lines[line_number - 1]}"
            )

    print("=== SIGNAL_REGISTRY_BLOCK ===")

    for line_number in range(551, 611):
        if line_number <= len(lines):
            print(
                f"{line_number:05d}: "
                f"{lines[line_number - 1]}"
            )

    print("db_writes_performed=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if supported_contains_rsi and registry_contains_rsi:
        print("root_cause=RSI_DISPATCH_ALREADY_PRESENT")
        print(
            "VERDICT="
            "POSTGRESQL_EDGE_BACKTEST_RSI_DISPATCH_V1_PRESENT"
        )
        return 0

    if function_rows:
        print(
            "root_cause="
            "RSI_SIGNAL_IMPLEMENTATION_EXISTS_DISPATCH_MISSING"
        )
        print(
            "VERDICT="
            "POSTGRESQL_EDGE_BACKTEST_RSI_DISPATCH_V1_PATCHABLE"
        )
        return 0

    print(
        "root_cause="
        "RSI_SIGNAL_IMPLEMENTATION_NOT_FOUND"
    )
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_BACKTEST_RSI_DISPATCH_V1_BLOCKED"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
