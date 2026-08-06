#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from dataclasses import dataclass
from typing import Any


ROOT = pathlib.Path("/opt/finam-core")

FILES = (
    ROOT / "src/scripts/build_edge_hypothesis_discovery_v1.py",
    ROOT / "src/scripts/build_edge_lab_runner_v1.py",
    ROOT / "src/scripts/build_profit_funnel_validated_edge_v2.py",
    ROOT / "src/scripts/backtest_runner.py",
)

OUT = pathlib.Path("/tmp/edge_cost_propagation_audit_v1")

REFERENCES_FILE = OUT / "cost_references.tsv"
ASSIGNMENTS_FILE = OUT / "cost_assignments.tsv"
WRITES_FILE = OUT / "edge_observation_writes.tsv"
CONTRACT_FILE = OUT / "contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


@dataclass(frozen=True, slots=True)
class SourceLine:
    file_path: str
    line_no: int
    category: str
    text: str


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
    node: ast.AST,
) -> str:
    value = ast.get_source_segment(source, node)
    return (value or "").strip().replace("\n", " ")[:1000]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    references: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    writes: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []

    for path in FILES:
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

        try:
            tree = ast.parse(source)
        except SyntaxError as error:
            unresolved.append(
                {
                    "scope": "SOURCE_FILE",
                    "identity": relative_path,
                    "reason": (
                        f"SYNTAX_ERROR:{error.lineno}:"
                        f"{error.msg}"
                    ),
                }
            )
            continue

        source_lines = source.splitlines()

        for line_no, line in enumerate(source_lines, start=1):
            lowered = line.lower()

            if "commission" in lowered:
                references.append(
                    {
                        "file_path": relative_path,
                        "line_no": line_no,
                        "category": "COMMISSION_REFERENCE",
                        "text": line.strip()[:1000],
                    }
                )

            if "slippage" in lowered:
                references.append(
                    {
                        "file_path": relative_path,
                        "line_no": line_no,
                        "category": "SLIPPAGE_REFERENCE",
                        "text": line.strip()[:1000],
                    }
                )

            if "edge_observation_v1" in lowered:
                references.append(
                    {
                        "file_path": relative_path,
                        "line_no": line_no,
                        "category": "EDGE_OBSERVATION_REFERENCE",
                        "text": line.strip()[:1000],
                    }
                )

            if "research_trade_v1" in lowered:
                references.append(
                    {
                        "file_path": relative_path,
                        "line_no": line_no,
                        "category": "RESEARCH_TRADE_REFERENCE",
                        "text": line.strip()[:1000],
                    }
                )

        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                text = source_segment(source, node).lower()

                if (
                    "commission" in text
                    or "slippage" in text
                    or "roundtrip_cost" in text
                    or "transaction_cost" in text
                ):
                    assignments.append(
                        {
                            "file_path": relative_path,
                            "line_no": getattr(node, "lineno", 0),
                            "node_type": type(node).__name__,
                            "text": source_segment(source, node),
                        }
                    )

            if not isinstance(node, ast.Call):
                continue

            call_text = source_segment(source, node)
            lowered_call = call_text.lower()

            if (
                "execute" in lowered_call
                and "edge_observation_v1" in lowered_call
            ):
                writes.append(
                    {
                        "file_path": relative_path,
                        "line_no": getattr(node, "lineno", 0),
                        "write_target": "analytics.edge_observation_v1",
                        "text": call_text,
                    }
                )

            if (
                "execute" in lowered_call
                and "research_trade_v1" in lowered_call
            ):
                writes.append(
                    {
                        "file_path": relative_path,
                        "line_no": getattr(node, "lineno", 0),
                        "write_target": "analytics.research_trade_v1",
                        "text": call_text,
                    }
                )

    discovery_commission_parameter_count = sum(
        row["file_path"].endswith(
            "build_edge_hypothesis_discovery_v1.py"
        )
        and "commission" in row["text"].lower()
        and "roundtrip_cost" in row["text"].lower()
        for row in assignments
    )

    discovery_zero_slippage_count = sum(
        row["file_path"].endswith(
            "build_edge_hypothesis_discovery_v1.py"
        )
        and "slippage" in row["text"].lower()
        and (
            "0.0" in row["text"]
            or "decimal(\"0\")" in row["text"].lower()
        )
        for row in assignments
    )

    edge_observation_write_count = sum(
        row["write_target"]
        == "analytics.edge_observation_v1"
        for row in writes
    )

    research_trade_write_count = sum(
        row["write_target"]
        == "analytics.research_trade_v1"
        for row in writes
    )

    runner_cost_reference_count = sum(
        row["file_path"].endswith(
            "build_edge_lab_runner_v1.py"
        )
        and row["category"] in {
            "COMMISSION_REFERENCE",
            "SLIPPAGE_REFERENCE",
        }
        for row in references
    )

    if discovery_commission_parameter_count == 0:
        unresolved.append(
            {
                "scope": "DISCOVERY",
                "identity": "commission",
                "reason": "ROUNDTRIP_COST_ASSIGNMENT_NOT_PROVEN",
            }
        )

    if discovery_zero_slippage_count == 0:
        unresolved.append(
            {
                "scope": "DISCOVERY",
                "identity": "slippage",
                "reason": "ZERO_SLIPPAGE_ASSIGNMENT_NOT_PROVEN",
            }
        )

    if edge_observation_write_count == 0:
        unresolved.append(
            {
                "scope": "WRITER",
                "identity": "analytics.edge_observation_v1",
                "reason": "WRITER_NOT_PROVEN",
            }
        )

    write_tsv(
        REFERENCES_FILE,
        (
            "file_path",
            "line_no",
            "category",
            "text",
        ),
        references,
    )

    write_tsv(
        ASSIGNMENTS_FILE,
        (
            "file_path",
            "line_no",
            "node_type",
            "text",
        ),
        assignments,
    )

    write_tsv(
        WRITES_FILE,
        (
            "file_path",
            "line_no",
            "write_target",
            "text",
        ),
        writes,
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
        stream.write("EDGE COST PROPAGATION AUDIT V1\n")
        stream.write("==============================\n\n")
        stream.write("MODE=STATIC_READ_ONLY\n")
        stream.write(
            "DISCOVERY_COMMISSION_SOURCE=ROUNDTRIP_COST\n"
        )
        stream.write(
            "DISCOVERY_SLIPPAGE_POLICY=ZERO\n"
        )
        stream.write(
            "DISCOVERY_COMMISSION_PARAMETER_COUNT="
            f"{discovery_commission_parameter_count}\n"
        )
        stream.write(
            "DISCOVERY_ZERO_SLIPPAGE_COUNT="
            f"{discovery_zero_slippage_count}\n"
        )
        stream.write(
            "EDGE_OBSERVATION_WRITE_COUNT="
            f"{edge_observation_write_count}\n"
        )
        stream.write(
            "RESEARCH_TRADE_WRITE_COUNT="
            f"{research_trade_write_count}\n"
        )
        stream.write(
            "RUNNER_COST_REFERENCE_COUNT="
            f"{runner_cost_reference_count}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("STRATEGY_CHANGED=0\n")
        stream.write("RISK_ENGINE_CHANGED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== EDGE COST PROPAGATION AUDIT V1 ===")
    print(
        "discovery_commission_parameter_count="
        f"{discovery_commission_parameter_count}"
    )
    print(
        "discovery_zero_slippage_count="
        f"{discovery_zero_slippage_count}"
    )
    print(
        "edge_observation_write_count="
        f"{edge_observation_write_count}"
    )
    print(
        "research_trade_write_count="
        f"{research_trade_write_count}"
    )
    print(
        "runner_cost_reference_count="
        f"{runner_cost_reference_count}"
    )
    print(f"unresolved_count={len(unresolved)}")
    print("db_writes_performed=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_COST_PROPAGATION_AUDIT_V1_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
