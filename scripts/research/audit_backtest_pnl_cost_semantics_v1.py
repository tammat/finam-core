#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from typing import Any


ROOT = pathlib.Path("/opt/finam-core")
TARGET = ROOT / "src/scripts/backtest_runner.py"
OUT = pathlib.Path("/tmp/backtest_pnl_cost_semantics_v1")

ASSIGNMENTS_FILE = OUT / "assignments.tsv"
DEPENDENCIES_FILE = OUT / "pnl_dependencies.tsv"
CONTRACT_FILE = OUT / "contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

TARGET_NAMES = {
    "entry_px",
    "exit_px",
    "pnl_gross",
    "gross_pnl",
    "commission",
    "slippage",
    "pnl_net",
    "net_pnl",
}


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def assigned_names(node: ast.Assign | ast.AnnAssign) -> list[str]:
    targets: list[ast.expr] = []

    if isinstance(node, ast.Assign):
        targets.extend(node.targets)
    else:
        targets.append(node.target)

    names: list[str] = []

    for target in targets:
        if isinstance(target, ast.Name):
            names.append(target.id)

    return names


def referenced_names(node: ast.AST | None) -> list[str]:
    if node is None:
        return []

    return sorted(
        {
            child.id
            for child in ast.walk(node)
            if isinstance(child, ast.Name)
            and isinstance(child.ctx, ast.Load)
        }
    )


def enclosing_function(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> str:
    current = node

    while current in parents:
        current = parents[current]

        if isinstance(
            current,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            return current.name

    return "<module>"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, str]] = []

    if not TARGET.is_file():
        raise RuntimeError(f"target_missing:{TARGET}")

    source = TARGET.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)

    parents: dict[ast.AST, ast.AST] = {}

    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent

    assignments: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        names = assigned_names(node)
        relevant_names = [
            name
            for name in names
            if name in TARGET_NAMES
        ]

        if not relevant_names:
            continue

        value_node = node.value
        expression = (
            ast.get_source_segment(source, value_node) or ""
            if value_node is not None
            else ""
        ).strip().replace("\n", " ")

        function_name = enclosing_function(node, parents)
        references = referenced_names(value_node)

        for assigned_name in relevant_names:
            assignments.append(
                {
                    "file_path": str(TARGET.relative_to(ROOT)),
                    "function_name": function_name,
                    "line_no": node.lineno,
                    "assigned_name": assigned_name,
                    "expression": expression,
                    "referenced_names": ",".join(references),
                }
            )

            for referenced_name in references:
                dependencies.append(
                    {
                        "function_name": function_name,
                        "line_no": node.lineno,
                        "target_name": assigned_name,
                        "depends_on": referenced_name,
                        "expression": expression,
                    }
                )

    net_assignments = [
        row
        for row in assignments
        if row["assigned_name"] in {"pnl_net", "net_pnl"}
    ]

    net_explicit_slippage_count = sum(
        "slippage" in row["referenced_names"].split(",")
        for row in net_assignments
    )

    net_explicit_commission_count = sum(
        "commission" in row["referenced_names"].split(",")
        for row in net_assignments
    )

    gross_uses_adjusted_price_count = 0

    for row in assignments:
        if row["assigned_name"] not in {
            "pnl_gross",
            "gross_pnl",
        }:
            continue

        refs = set(row["referenced_names"].split(","))

        if {"entry_px", "exit_px"} & refs:
            gross_uses_adjusted_price_count += 1

    entry_apply_cost_count = sum(
        row["assigned_name"] == "entry_px"
        and "apply_costs(" in row["expression"]
        for row in assignments
    )

    exit_apply_cost_count = sum(
        row["assigned_name"] == "exit_px"
        and "apply_costs(" in row["expression"]
        for row in assignments
    )

    if not net_assignments:
        unresolved.append(
            {
                "scope": "PNL",
                "identity": "net_pnl",
                "reason": "NET_PNL_ASSIGNMENT_NOT_FOUND",
            }
        )

    write_tsv(
        ASSIGNMENTS_FILE,
        (
            "file_path",
            "function_name",
            "line_no",
            "assigned_name",
            "expression",
            "referenced_names",
        ),
        assignments,
    )

    write_tsv(
        DEPENDENCIES_FILE,
        (
            "function_name",
            "line_no",
            "target_name",
            "depends_on",
            "expression",
        ),
        dependencies,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    with CONTRACT_FILE.open("w", encoding="utf-8") as stream:
        stream.write("BACKTEST PNL COST SEMANTICS V1\n")
        stream.write("==============================\n\n")
        stream.write("MODE=STATIC_READ_ONLY\n")
        stream.write(
            f"NET_ASSIGNMENT_COUNT={len(net_assignments)}\n"
        )
        stream.write(
            "NET_EXPLICIT_COMMISSION_COUNT="
            f"{net_explicit_commission_count}\n"
        )
        stream.write(
            "NET_EXPLICIT_SLIPPAGE_COUNT="
            f"{net_explicit_slippage_count}\n"
        )
        stream.write(
            "ENTRY_APPLY_COST_COUNT="
            f"{entry_apply_cost_count}\n"
        )
        stream.write(
            "EXIT_APPLY_COST_COUNT="
            f"{exit_apply_cost_count}\n"
        )
        stream.write(
            "GROSS_USES_ADJUSTED_PRICE_COUNT="
            f"{gross_uses_adjusted_price_count}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write("SOURCE_CHANGED=0\n")
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== BACKTEST PNL COST SEMANTICS V1 ===")
    print(f"net_assignment_count={len(net_assignments)}")
    print(
        "net_explicit_commission_count="
        f"{net_explicit_commission_count}"
    )
    print(
        "net_explicit_slippage_count="
        f"{net_explicit_slippage_count}"
    )
    print(f"entry_apply_cost_count={entry_apply_cost_count}")
    print(f"exit_apply_cost_count={exit_apply_cost_count}")
    print(
        "gross_uses_adjusted_price_count="
        f"{gross_uses_adjusted_price_count}"
    )
    print(f"unresolved_count={len(unresolved)}")
    print("source_changed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=BACKTEST_PNL_COST_SEMANTICS_V1_READY")

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
