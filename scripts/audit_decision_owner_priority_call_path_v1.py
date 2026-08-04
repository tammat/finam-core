#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()
OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_priority_call_path_v1"
)

EDGES_FILE = OUTPUT_DIR / "call_path_edges.tsv"
OWNER_FILE = OUTPUT_DIR / "owner_evidence.tsv"
BROKER_FILE = OUTPUT_DIR / "broker_boundary.tsv"
REPORT_FILE = OUTPUT_DIR / "call_path_report.txt"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

TARGETS = (
    (
        "RISK",
        "src/finam_core/risk/portfolio_risk_gate.py",
        "check",
    ),
    (
        "RUNTIME",
        "src/finam_core/pipelines/paper_pipeline.py",
        "_execute_br_signal_in_paper",
    ),
    (
        "EXECUTION",
        "src/finam_core/execution/execution_dispatcher.py",
        "place_limit_order",
    ),
    (
        "BROKER_LIMIT",
        "src/finam_core/adapters/grpc/orders_client.py",
        "place_limit_order",
    ),
    (
        "BROKER_MARKET",
        "src/finam_core/adapters/grpc/orders_client.py",
        "place_market_order",
    ),
)

CALLER_TARGETS = (
    (
        "PIPELINE",
        "src/finam_core/pipelines/paper_pipeline.py",
        "_on_quote_impl",
    ),
    (
        "RUNTIME",
        "src/finam_core/pipelines/paper_pipeline.py",
        "_execute_br_signal_in_paper",
    ),
    (
        "EXECUTION",
        "src/finam_core/execution/execution_dispatcher.py",
        "execute",
    ),
    (
        "EXECUTION_LIMIT",
        "src/finam_core/execution/execution_dispatcher.py",
        "place_limit_order",
    ),
)


@dataclass(frozen=True, slots=True)
class FunctionNode:
    role: str
    path: str
    function: str
    line: int
    end_line: int
    calls: tuple[str, ...]
    returns: tuple[str, ...]
    source: str


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        parts: list[str] = []
        current: ast.expr = node.func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return "<unknown>"


def return_shape(node: ast.Return) -> str:
    value = node.value

    if value is None:
        return "None"

    if isinstance(value, ast.Name):
        return f"Name:{value.id}"

    if isinstance(value, ast.Constant):
        return f"Constant:{value.value!r}"

    if isinstance(value, ast.Tuple):
        return "Tuple"

    if isinstance(value, ast.Dict):
        return "Dict"

    if isinstance(value, ast.Call):
        return f"Call:{call_name(value)}"

    return type(value).__name__


def load_function(
    role: str,
    relative_path: str,
    function_name: str,
) -> FunctionNode:
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(
            f"target_file_missing:{relative_path}"
        )

    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)

    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        )
        and node.name == function_name
    ]

    if len(matches) != 1:
        raise RuntimeError(
            "target_function_not_unique:"
            f"{relative_path}:"
            f"{function_name}:"
            f"{len(matches)}"
        )

    node = matches[0]
    segment = ast.get_source_segment(
        source,
        node,
    ) or ""

    calls = tuple(
        sorted(
            {
                call_name(child)
                for child in ast.walk(node)
                if isinstance(child, ast.Call)
            }
        )
    )

    returns = tuple(
        return_shape(child)
        for child in ast.walk(node)
        if isinstance(child, ast.Return)
    )

    return FunctionNode(
        role=role,
        path=relative_path,
        function=function_name,
        line=node.lineno,
        end_line=node.end_lineno or node.lineno,
        calls=calls,
        returns=returns,
        source=segment,
    )


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
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
        )
        writer.writeheader()
        writer.writerows(rows)


def contains_call(
    node: FunctionNode,
    markers: tuple[str, ...],
) -> tuple[str, ...]:
    return tuple(
        call
        for call in node.calls
        if any(
            marker in call
            for marker in markers
        )
    )


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    unresolved: list[dict[str, object]] = []
    nodes: list[FunctionNode] = []

    for role, path, function in (
        *TARGETS,
        *CALLER_TARGETS,
    ):
        try:
            nodes.append(
                load_function(
                    role,
                    path,
                    function,
                )
            )
        except Exception as exc:
            unresolved.append(
                {
                    "role": role,
                    "path": path,
                    "function": function,
                    "reason": str(exc),
                }
            )

    node_index = {
        (node.path, node.function): node
        for node in nodes
    }

    edge_specs = (
        (
            "PIPELINE_TO_RISK",
            (
                "src/finam_core/pipelines/paper_pipeline.py",
                "_on_quote_impl",
            ),
            (
                "portfolio_risk_gate",
                ".check",
            ),
        ),
        (
            "PIPELINE_TO_RUNTIME_GATE",
            (
                "src/finam_core/pipelines/paper_pipeline.py",
                "_on_quote_impl",
            ),
            (
                "_execute_br_signal_in_paper",
            ),
        ),
        (
            "RUNTIME_TO_EXECUTION",
            (
                "src/finam_core/pipelines/paper_pipeline.py",
                "_execute_br_signal_in_paper",
            ),
            (
                "execution_dispatcher",
                ".execute",
                ".place_limit_order",
            ),
        ),
        (
            "EXECUTION_TO_BROKER",
            (
                "src/finam_core/execution/execution_dispatcher.py",
                "place_limit_order",
            ),
            (
                "orders_client",
                ".place_limit_order",
            ),
        ),
    )

    edge_rows: list[dict[str, object]] = []

    for edge_name, source_key, markers in edge_specs:
        source = node_index.get(source_key)

        if source is None:
            edge_rows.append(
                {
                    "edge": edge_name,
                    "source_path": source_key[0],
                    "source_function": source_key[1],
                    "matched_calls": "",
                    "reachable": 0,
                }
            )
            continue

        matches = contains_call(
            source,
            markers,
        )

        edge_rows.append(
            {
                "edge": edge_name,
                "source_path": source.path,
                "source_function": source.function,
                "matched_calls": ",".join(matches),
                "reachable": int(bool(matches)),
            }
        )

    owner_rows: list[dict[str, object]] = []

    owner_specs = (
        (
            "RISK",
            (
                "src/finam_core/risk/portfolio_risk_gate.py",
                "check",
            ),
            "METHOD",
            "AUTHORITATIVE_GATE_CANDIDATE",
        ),
        (
            "RUNTIME",
            (
                "src/finam_core/pipelines/paper_pipeline.py",
                "_execute_br_signal_in_paper",
            ),
            "METHOD",
            "PRE_EXECUTION_GATE_CANDIDATE",
        ),
        (
            "EXECUTION",
            (
                "src/finam_core/execution/execution_dispatcher.py",
                "place_limit_order",
            ),
            "METHOD",
            "ORDER_DISPATCH_CANDIDATE",
        ),
    )

    for stage, key, granularity, classification in owner_specs:
        node = node_index.get(key)

        owner_rows.append(
            {
                "stage": stage,
                "path": key[0],
                "symbol": key[1],
                "granularity": granularity,
                "classification": classification,
                "exists": int(node is not None),
                "return_count": (
                    len(node.returns)
                    if node is not None
                    else 0
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    broker_nodes = [
        node
        for node in nodes
        if node.path
        == "src/finam_core/adapters/grpc/orders_client.py"
        and node.function in {
            "place_limit_order",
            "place_market_order",
        }
    ]

    broker_rows = [
        {
            "stage": "BROKER",
            "path": (
                "src/finam_core/adapters/grpc/"
                "orders_client.py"
            ),
            "owner_symbol": "OrdersClient",
            "owner_granularity": "CLASS_BOUNDARY",
            "limit_method_present": int(
                any(
                    node.function == "place_limit_order"
                    for node in broker_nodes
                )
            ),
            "market_method_present": int(
                any(
                    node.function == "place_market_order"
                    for node in broker_nodes
                )
            ),
            "classification": (
                "BROKER_ADAPTER_BOUNDARY_CANDIDATE"
            ),
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }
    ]

    write_tsv(
        EDGES_FILE,
        (
            "edge",
            "source_path",
            "source_function",
            "matched_calls",
            "reachable",
        ),
        edge_rows,
    )

    write_tsv(
        OWNER_FILE,
        (
            "stage",
            "path",
            "symbol",
            "granularity",
            "classification",
            "exists",
            "return_count",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        owner_rows,
    )

    write_tsv(
        BROKER_FILE,
        (
            "stage",
            "path",
            "owner_symbol",
            "owner_granularity",
            "limit_method_present",
            "market_method_present",
            "classification",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        broker_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "role",
            "path",
            "function",
            "reason",
        ),
        unresolved,
    )

    with REPORT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "DECISION OWNER PRIORITY CALL PATH V1\n"
        )
        stream.write(
            "====================================\n\n"
        )

        for row in edge_rows:
            stream.write(
                f"EDGE={row['edge']} "
                f"REACHABLE={row['reachable']} "
                f"CALLS={row['matched_calls']}\n"
            )

        stream.write("\n")
        stream.write(
            "BROKER_OWNER_GRANULARITY=CLASS_BOUNDARY\n"
        )
        stream.write(
            "BROKER_OWNER_SYMBOL=OrdersClient\n"
        )
        stream.write(
            "OWNER_ASSIGNMENT_PERFORMED=0\n"
        )
        stream.write(
            "RUNTIME_INSTRUMENTATION=0\n"
        )

    reachable_count = sum(
        int(row["reachable"])
        for row in edge_rows
    )

    print(
        "=== AUDIT DECISION OWNER "
        "PRIORITY CALL PATH V1 ==="
    )
    print(f"target_function_count={len(nodes)}")
    print(f"unresolved_count={len(unresolved)}")
    print(f"call_path_edge_count={len(edge_rows)}")
    print(f"reachable_edge_count={reachable_count}")

    for row in edge_rows:
        print(
            f"EDGE name={row['edge']} "
            f"reachable={row['reachable']} "
            f"matched_calls={row['matched_calls']}"
        )

    print("broker_owner_granularity=CLASS_BOUNDARY")
    print("broker_owner_symbol=OrdersClient")
    print("confirmed_owner_count=0")
    print("owner_assignment_performed=0")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "DECISION_OWNER_PRIORITY_CALL_PATH_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
