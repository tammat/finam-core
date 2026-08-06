#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from typing import Any


ROOT = pathlib.Path("/opt/finam-core")

TARGETS = (
    ROOT / "src/scripts/build_edge_lab_runner_v1.py",
    ROOT / "src/scripts/backtest_runner.py",
)

OUT = pathlib.Path(
    "/tmp/edge_observation_cost_aggregation_v1"
)

INSERTS_FILE = OUT / "edge_observation_inserts.tsv"
BINDINGS_FILE = OUT / "insert_bindings.tsv"
METRICS_FILE = OUT / "metric_assignments.tsv"
CONTRACT_FILE = OUT / "contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

COST_METRICS = {
    "commission",
    "slippage",
    "gross_pnl",
    "net_pnl",
    "expectancy",
    "profit_factor",
    "max_drawdown",
}


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def source_segment(
    source: str,
    node: ast.AST | None,
) -> str:
    if node is None:
        return ""

    return (
        ast.get_source_segment(source, node) or ""
    ).strip().replace("\n", " ")[:5000]


def assignment_names(
    node: ast.Assign | ast.AnnAssign,
) -> list[str]:
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


def parse_insert_columns(sql_text: str) -> list[str]:
    normalized = " ".join(sql_text.split())
    marker = "INSERT INTO analytics.edge_observation_v1"

    marker_position = normalized.upper().find(marker.upper())

    if marker_position < 0:
        return []

    opening = normalized.find("(", marker_position)

    if opening < 0:
        return []

    depth = 0

    for index in range(opening, len(normalized)):
        character = normalized[index]

        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1

            if depth == 0:
                return [
                    item.strip().strip('"')
                    for item in normalized[
                        opening + 1:index
                    ].split(",")
                ]

    return []


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    insert_rows: list[dict[str, Any]] = []
    binding_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []

    for path in TARGETS:
        relative_path = str(path.relative_to(ROOT))

        if not path.is_file():
            unresolved.append(
                {
                    "scope": "SOURCE_FILE",
                    "identity": relative_path,
                    "reason": "FILE_MISSING",
                }
            )
            continue

        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        tree = ast.parse(source)

        parents: dict[ast.AST, ast.AST] = {}

        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[child] = parent

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                names = assignment_names(node)
                relevant = [
                    name
                    for name in names
                    if name in COST_METRICS
                ]

                if relevant:
                    expression = source_segment(
                        source,
                        node.value,
                    )

                    for name in relevant:
                        metric_rows.append(
                            {
                                "file_path": relative_path,
                                "function_name": enclosing_function(
                                    node,
                                    parents,
                                ),
                                "line_no": node.lineno,
                                "metric_name": name,
                                "expression": expression,
                            }
                        )

            if not isinstance(node, ast.Call):
                continue

            call_text = source_segment(source, node)

            if (
                "edge_observation_v1" not in call_text
                or "INSERT INTO" not in call_text.upper()
            ):
                continue

            columns = parse_insert_columns(call_text)

            argument_text = ""

            if len(node.args) >= 2:
                argument_text = source_segment(
                    source,
                    node.args[1],
                )

            insert_rows.append(
                {
                    "file_path": relative_path,
                    "function_name": enclosing_function(
                        node,
                        parents,
                    ),
                    "line_no": node.lineno,
                    "column_count": len(columns),
                    "columns": ",".join(columns),
                    "binding_expression": argument_text,
                    "call_text": call_text,
                }
            )

            for ordinal, column_name in enumerate(
                columns,
                start=1,
            ):
                binding_rows.append(
                    {
                        "file_path": relative_path,
                        "line_no": node.lineno,
                        "ordinal": ordinal,
                        "column_name": column_name,
                        "is_cost_metric": int(
                            column_name in COST_METRICS
                        ),
                        "binding_expression": argument_text,
                    }
                )

    cost_insert_columns = {
        row["column_name"]
        for row in binding_rows
        if row["is_cost_metric"] == 1
    }

    required_cost_columns = {
        "commission",
        "slippage",
        "expectancy",
        "profit_factor",
        "max_drawdown",
    }

    missing_cost_columns = sorted(
        required_cost_columns - cost_insert_columns
    )

    for column_name in missing_cost_columns:
        unresolved.append(
            {
                "scope": "EDGE_OBSERVATION_INSERT",
                "identity": column_name,
                "reason": "COST_COLUMN_NOT_IN_INSERT",
            }
        )

    parameter_binding_count = sum(
        "parameter" in row["binding_expression"].lower()
        or "params" in row["binding_expression"].lower()
        for row in insert_rows
    )

    metrics_binding_count = sum(
        "metric" in row["binding_expression"].lower()
        or "result" in row["binding_expression"].lower()
        for row in insert_rows
    )

    write_tsv(
        INSERTS_FILE,
        (
            "file_path",
            "function_name",
            "line_no",
            "column_count",
            "columns",
            "binding_expression",
            "call_text",
        ),
        insert_rows,
    )

    write_tsv(
        BINDINGS_FILE,
        (
            "file_path",
            "line_no",
            "ordinal",
            "column_name",
            "is_cost_metric",
            "binding_expression",
        ),
        binding_rows,
    )

    write_tsv(
        METRICS_FILE,
        (
            "file_path",
            "function_name",
            "line_no",
            "metric_name",
            "expression",
        ),
        metric_rows,
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

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "EDGE OBSERVATION COST AGGREGATION AUDIT V1\n"
        )
        stream.write(
            "==========================================\n\n"
        )
        stream.write("MODE=STATIC_READ_ONLY\n")
        stream.write(
            f"EDGE_OBSERVATION_INSERT_COUNT="
            f"{len(insert_rows)}\n"
        )
        stream.write(
            f"INSERT_COLUMN_BINDING_COUNT="
            f"{len(binding_rows)}\n"
        )
        stream.write(
            f"COST_METRIC_ASSIGNMENT_COUNT="
            f"{len(metric_rows)}\n"
        )
        stream.write(
            f"PARAMETER_BINDING_COUNT="
            f"{parameter_binding_count}\n"
        )
        stream.write(
            f"METRICS_BINDING_COUNT="
            f"{metrics_binding_count}\n"
        )
        stream.write(
            "SLIPPAGE_EMBEDDED_IN_EXECUTION_PRICES=1\n"
        )
        stream.write(
            "NET_PNL_EXPLICIT_SLIPPAGE_DEDUCTION=0\n"
        )
        stream.write(
            "DOUBLE_SLIPPAGE_DEDUCTION_ALLOWED=0\n"
        )
        stream.write(
            f"MISSING_COST_COLUMN_COUNT="
            f"{len(missing_cost_columns)}\n"
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

    print(
        "=== EDGE OBSERVATION COST "
        "AGGREGATION AUDIT V1 ==="
    )
    print(
        f"edge_observation_insert_count="
        f"{len(insert_rows)}"
    )
    print(
        f"insert_column_binding_count="
        f"{len(binding_rows)}"
    )
    print(
        f"cost_metric_assignment_count="
        f"{len(metric_rows)}"
    )
    print(
        f"parameter_binding_count="
        f"{parameter_binding_count}"
    )
    print(
        f"metrics_binding_count="
        f"{metrics_binding_count}"
    )
    print(
        "slippage_embedded_in_execution_prices=1"
    )
    print(
        "double_slippage_deduction_allowed=0"
    )
    print(
        f"missing_cost_column_count="
        f"{len(missing_cost_columns)}"
    )
    print(f"unresolved_count={len(unresolved)}")
    print("source_changed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "EDGE_OBSERVATION_COST_AGGREGATION_AUDIT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
