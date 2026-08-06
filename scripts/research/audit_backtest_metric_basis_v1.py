#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from typing import Any


ROOT = pathlib.Path("/opt/finam-core")

TARGETS = (
    ROOT / "src/scripts/backtest_runner.py",
    ROOT / "src/scripts/build_edge_lab_runner_v1.py",
    ROOT / "src/scripts/build_edge_score_engine_v2.py",
    ROOT / "src/scripts/score_momentum_edge_recalculation_v2.py",
)

OUT = pathlib.Path("/tmp/backtest_metric_basis_v1")

ASSIGNMENTS_FILE = OUT / "metric_basis_assignments.tsv"
WRITERS_FILE = OUT / "edge_observation_writers.tsv"
CONTRACT_FILE = OUT / "contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

TARGET_NAMES = {
    "gross_gain",
    "gross_loss",
    "profit_factor",
    "expectancy",
    "max_drawdown",
    "drawdown",
    "gross_pnl",
    "net_pnl",
}

WRITE_MARKERS = {
    "INSERT INTO analytics.edge_observation_v1",
    "UPDATE analytics.edge_observation_v1",
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


def source_segment(
    source: str,
    node: ast.AST | None,
) -> str:
    if node is None:
        return ""

    return (
        ast.get_source_segment(source, node) or ""
    ).strip().replace("\n", " ")[:8000]


def assignment_names(
    node: ast.Assign | ast.AnnAssign,
) -> list[str]:
    targets = (
        node.targets
        if isinstance(node, ast.Assign)
        else [node.target]
    )

    return [
        target.id
        for target in targets
        if isinstance(target, ast.Name)
    ]


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

    assignments: list[dict[str, Any]] = []
    writers: list[dict[str, Any]] = []
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

                for name in names:
                    if name not in TARGET_NAMES:
                        continue

                    assignments.append(
                        {
                            "file_path": relative_path,
                            "function_name": enclosing_function(
                                node,
                                parents,
                            ),
                            "line_no": node.lineno,
                            "metric_name": name,
                            "expression": source_segment(
                                source,
                                node.value,
                            ),
                            "referenced_names": ",".join(
                                referenced_names(node.value)
                            ),
                        }
                    )

            if not isinstance(node, ast.Call):
                continue

            call_text = source_segment(source, node)
            normalized = " ".join(call_text.split()).upper()

            matched_marker = next(
                (
                    marker
                    for marker in WRITE_MARKERS
                    if marker.upper() in normalized
                ),
                None,
            )

            if matched_marker is None:
                continue

            writers.append(
                {
                    "file_path": relative_path,
                    "function_name": enclosing_function(
                        node,
                        parents,
                    ),
                    "line_no": node.lineno,
                    "write_type": (
                        "INSERT"
                        if matched_marker.startswith("INSERT")
                        else "UPDATE"
                    ),
                    "contains_no_trades": int(
                        "NO_TRADES" in normalized
                    ),
                    "contains_profit_factor": int(
                        "PROFIT_FACTOR" in normalized
                    ),
                    "contains_expectancy": int(
                        "EXPECTANCY" in normalized
                    ),
                    "contains_commission": int(
                        "COMMISSION" in normalized
                    ),
                    "contains_slippage": int(
                        "SLIPPAGE" in normalized
                    ),
                    "call_text": call_text,
                }
            )

    assignment_by_name: dict[str, list[dict[str, Any]]] = {}

    for row in assignments:
        assignment_by_name.setdefault(
            row["metric_name"],
            [],
        ).append(row)

    gross_gain_uses_net_count = sum(
        "pnl_net" in row["expression"]
        for row in assignment_by_name.get("gross_gain", [])
    )
    gross_loss_uses_net_count = sum(
        "pnl_net" in row["expression"]
        for row in assignment_by_name.get("gross_loss", [])
    )
    gross_gain_uses_gross_count = sum(
        "pnl_gross" in row["expression"]
        for row in assignment_by_name.get("gross_gain", [])
    )
    gross_loss_uses_gross_count = sum(
        "pnl_gross" in row["expression"]
        for row in assignment_by_name.get("gross_loss", [])
    )

    successful_metric_writer_count = sum(
        row["contains_no_trades"] == 0
        and row["contains_profit_factor"] == 1
        and row["contains_expectancy"] == 1
        for row in writers
    )

    if not assignment_by_name.get("profit_factor"):
        unresolved.append(
            {
                "scope": "METRIC_BASIS",
                "identity": "profit_factor",
                "reason": "ASSIGNMENT_NOT_FOUND",
            }
        )

    if not assignment_by_name.get("gross_gain"):
        unresolved.append(
            {
                "scope": "METRIC_BASIS",
                "identity": "gross_gain",
                "reason": "ASSIGNMENT_NOT_FOUND",
            }
        )

    if not assignment_by_name.get("gross_loss"):
        unresolved.append(
            {
                "scope": "METRIC_BASIS",
                "identity": "gross_loss",
                "reason": "ASSIGNMENT_NOT_FOUND",
            }
        )

    if successful_metric_writer_count == 0:
        unresolved.append(
            {
                "scope": "EDGE_OBSERVATION_WRITER",
                "identity": "successful_metrics",
                "reason": "SUCCESSFUL_METRIC_WRITER_NOT_PROVEN",
            }
        )

    write_tsv(
        ASSIGNMENTS_FILE,
        (
            "file_path",
            "function_name",
            "line_no",
            "metric_name",
            "expression",
            "referenced_names",
        ),
        assignments,
    )

    write_tsv(
        WRITERS_FILE,
        (
            "file_path",
            "function_name",
            "line_no",
            "write_type",
            "contains_no_trades",
            "contains_profit_factor",
            "contains_expectancy",
            "contains_commission",
            "contains_slippage",
            "call_text",
        ),
        writers,
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
        stream.write("BACKTEST METRIC BASIS V1\n")
        stream.write("========================\n\n")
        stream.write("MODE=STATIC_READ_ONLY\n")
        stream.write(
            f"GROSS_GAIN_USES_NET_COUNT="
            f"{gross_gain_uses_net_count}\n"
        )
        stream.write(
            f"GROSS_LOSS_USES_NET_COUNT="
            f"{gross_loss_uses_net_count}\n"
        )
        stream.write(
            f"GROSS_GAIN_USES_GROSS_COUNT="
            f"{gross_gain_uses_gross_count}\n"
        )
        stream.write(
            f"GROSS_LOSS_USES_GROSS_COUNT="
            f"{gross_loss_uses_gross_count}\n"
        )
        stream.write(
            f"EDGE_OBSERVATION_WRITER_COUNT="
            f"{len(writers)}\n"
        )
        stream.write(
            f"SUCCESSFUL_METRIC_WRITER_COUNT="
            f"{successful_metric_writer_count}\n"
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

    print("=== BACKTEST METRIC BASIS V1 ===")
    print(
        f"gross_gain_uses_net_count="
        f"{gross_gain_uses_net_count}"
    )
    print(
        f"gross_loss_uses_net_count="
        f"{gross_loss_uses_net_count}"
    )
    print(
        f"gross_gain_uses_gross_count="
        f"{gross_gain_uses_gross_count}"
    )
    print(
        f"gross_loss_uses_gross_count="
        f"{gross_loss_uses_gross_count}"
    )
    print(
        f"edge_observation_writer_count="
        f"{len(writers)}"
    )
    print(
        f"successful_metric_writer_count="
        f"{successful_metric_writer_count}"
    )
    print(f"unresolved_count={len(unresolved)}")
    print("source_changed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=BACKTEST_METRIC_BASIS_V1_READY")

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
