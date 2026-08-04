#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from dataclasses import dataclass
from typing import Iterable


ROOT = pathlib.Path("/opt/finam-core").resolve()

EXECUTION_FILE = (
    ROOT
    / "src/finam_core/execution/execution_dispatcher.py"
)

BROKER_FILE = (
    ROOT
    / "src/finam_core/adapters/grpc/orders_client.py"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/execution_broker_result_ownership_v1"
)

EXECUTION_METHODS_FILE = OUTPUT_DIR / "execution_methods.tsv"
BROKER_METHODS_FILE = OUTPUT_DIR / "broker_methods.tsv"
EDGES_FILE = OUTPUT_DIR / "result_flow_edges.tsv"
RESULTS_FILE = OUTPUT_DIR / "result_contracts.tsv"
EXCEPTIONS_FILE = OUTPUT_DIR / "exception_contracts.tsv"
OWNERS_FILE = OUTPUT_DIR / "ownership_candidates.tsv"
EVIDENCE_FILE = OUTPUT_DIR / "evidence.txt"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

EXECUTION_TARGETS = (
    ("ExecutionDispatcher", "execute"),
    ("ExecutionDispatcher", "place_limit_order"),
)

BROKER_TARGETS = (
    ("FinamOrdersClient", "place_limit_order"),
    ("FinamOrdersClient", "place_market_order"),
)
ORDER_CALL_MARKERS = (
    "place_limit_order",
    "place_market_order",
    "send_order",
    "submit_order",
)

ACK_MARKERS = (
    "ack",
    "accepted",
    "success",
    "order_id",
    "transaction_id",
    "client_order_id",
)

REJECT_MARKERS = (
    "reject",
    "rejected",
    "denied",
    "failed",
    "error",
    "exception",
)

STATUS_MARKERS = (
    "status",
    "result",
    "outcome",
    "reason",
    "reason_code",
)


@dataclass(frozen=True, slots=True)
class FunctionInfo:
    owner_layer: str
    path: str
    function: str
    line: int
    end_line: int
    node: ast.FunctionDef | ast.AsyncFunctionDef
    source: str
    calls: tuple[str, ...]
    returns: tuple[str, ...]
    raises: tuple[str, ...]
    except_handlers: tuple[str, ...]
    assigned_calls: tuple[str, ...]


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return ""


def call_name(node: ast.Call) -> str:
    return dotted_name(node.func) or "<unknown>"


def source_text(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""

    return ast.get_source_segment(source, node) or ""


def return_shape(node: ast.Return) -> str:
    value = node.value

    if value is None:
        return "None"

    if isinstance(value, ast.Name):
        return f"Name:{value.id}"

    if isinstance(value, ast.Constant):
        return f"Constant:{value.value!r}"

    if isinstance(value, ast.Dict):
        # Для определения формы результата достаточно количества ключей.
        # Нельзя вызывать ast.get_source_segment с пустым source:
        # координаты AST относятся к исходному файлу и приводят к IndexError.
        return f"Dict:{len(value.keys)}"

    if isinstance(value, ast.Tuple):
        return f"Tuple:{len(value.elts)}"

    if isinstance(value, ast.Call):
        return f"Call:{call_name(value)}"

    if isinstance(value, ast.Attribute):
        return f"Attribute:{dotted_name(value)}"

    return type(value).__name__


def exception_name(node: ast.ExceptHandler) -> str:
    if node.type is None:
        return "BARE_EXCEPT"

    return dotted_name(node.type) or type(node.type).__name__


def find_function(
    *,
    owner_layer: str,
    path: pathlib.Path,
    class_name: str,
    function_name: str,
) -> FunctionInfo:
    if not path.is_file():
        raise RuntimeError(f"file_missing:{path}")

    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)

    qualified_target = (
        f"{class_name}.{function_name}"
    )

    matches: list[
        ast.FunctionDef | ast.AsyncFunctionDef
    ] = []

    class QualifiedFunctionVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.scope: list[str] = []

        def visit_ClassDef(
            self,
            node: ast.ClassDef,
        ) -> None:
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def _visit_function(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            qualified_name = ".".join(
                [*self.scope, node.name]
            )

            if qualified_name == qualified_target:
                matches.append(node)

            # Вложенная функция получает собственную область.
            self.scope.append(node.name)
            self.generic_visit(node)
            self.scope.pop()

        def visit_FunctionDef(
            self,
            node: ast.FunctionDef,
        ) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(
            self,
            node: ast.AsyncFunctionDef,
        ) -> None:
            self._visit_function(node)

    QualifiedFunctionVisitor().visit(tree)

    if len(matches) != 1:
        discovered: list[str] = []

        class DiscoveryVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.scope: list[str] = []

            def visit_ClassDef(
                self,
                node: ast.ClassDef,
            ) -> None:
                self.scope.append(node.name)
                self.generic_visit(node)
                self.scope.pop()

            def _visit_function(
                self,
                node: ast.FunctionDef | ast.AsyncFunctionDef,
            ) -> None:
                if node.name == function_name:
                    discovered.append(
                        ".".join(
                            [*self.scope, node.name]
                        )
                    )

                self.scope.append(node.name)
                self.generic_visit(node)
                self.scope.pop()

            def visit_FunctionDef(
                self,
                node: ast.FunctionDef,
            ) -> None:
                self._visit_function(node)

            def visit_AsyncFunctionDef(
                self,
                node: ast.AsyncFunctionDef,
            ) -> None:
                self._visit_function(node)

        DiscoveryVisitor().visit(tree)

        raise RuntimeError(
            "qualified_function_not_unique:"
            f"{path.relative_to(ROOT)}:"
            f"{qualified_target}:"
            f"matches={len(matches)}:"
            f"discovered={','.join(sorted(discovered))}"
        )

    node = matches[0]
    segment = source_text(source, node)

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

    raises = tuple(
        source_text(source, child.exc)
        for child in ast.walk(node)
        if isinstance(child, ast.Raise)
        and child.exc is not None
    )

    except_handlers = tuple(
        exception_name(child)
        for child in ast.walk(node)
        if isinstance(child, ast.ExceptHandler)
    )

    assigned_calls: list[str] = []

    for child in ast.walk(node):
        if not isinstance(
            child,
            (ast.Assign, ast.AnnAssign),
        ):
            continue

        value = child.value

        if isinstance(value, ast.Await):
            value = value.value

        if isinstance(value, ast.Call):
            assigned_calls.append(
                call_name(value)
            )

    return FunctionInfo(
        owner_layer=owner_layer,
        path=str(path.relative_to(ROOT)),
        function=function_name,
        line=node.lineno,
        end_line=node.end_lineno or node.lineno,
        node=node,
        source=segment,
        calls=calls,
        returns=returns,
        raises=raises,
        except_handlers=except_handlers,
        assigned_calls=tuple(
            sorted(set(assigned_calls))
        ),
    )


def text_hits(
    text: str,
    markers: Iterable[str],
) -> tuple[str, ...]:
    normalized = text.lower()

    return tuple(
        marker
        for marker in markers
        if marker.lower() in normalized
    )


def result_contract_rows(
    functions: list[FunctionInfo],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for function in functions:
        ack_hits = text_hits(
            function.source,
            ACK_MARKERS,
        )
        reject_hits = text_hits(
            function.source,
            REJECT_MARKERS,
        )
        status_hits = text_hits(
            function.source,
            STATUS_MARKERS,
        )

        for index, shape in enumerate(
            function.returns,
            start=1,
        ):
            rows.append(
                {
                    "layer": function.owner_layer,
                    "path": function.path,
                    "function": function.function,
                    "line": function.line,
                    "return_index": index,
                    "return_shape": shape,
                    "ack_markers": ",".join(ack_hits),
                    "reject_markers": ",".join(
                        reject_hits
                    ),
                    "status_markers": ",".join(
                        status_hits
                    ),
                }
            )

    return rows


def exception_rows(
    functions: list[FunctionInfo],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for function in functions:
        for exception in function.except_handlers:
            rows.append(
                {
                    "layer": function.owner_layer,
                    "path": function.path,
                    "function": function.function,
                    "line": function.line,
                    "contract_type": "EXCEPT_HANDLER",
                    "exception": exception,
                }
            )

        for raise_expr in function.raises:
            rows.append(
                {
                    "layer": function.owner_layer,
                    "path": function.path,
                    "function": function.function,
                    "line": function.line,
                    "contract_type": "RAISE",
                    "exception": raise_expr,
                }
            )

    return rows


def edge_rows(
    execution_functions: list[FunctionInfo],
    broker_functions: list[FunctionInfo],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    broker_names = {
        function.function
        for function in broker_functions
    }

    for function in execution_functions:
        matched = tuple(
            call
            for call in function.calls
            if any(
                call.endswith(name)
                for name in broker_names
            )
        )

        assigned = tuple(
            call
            for call in function.assigned_calls
            if any(
                call.endswith(name)
                for name in broker_names
            )
        )

        rows.append(
            {
                "edge": (
                    "EXECUTION_TO_BROKER:"
                    f"{function.function}"
                ),
                "source_path": function.path,
                "source_function": function.function,
                "matched_calls": ",".join(matched),
                "assigned_result_calls": ",".join(
                    assigned
                ),
                "reachable": int(bool(matched)),
                "broker_result_captured": int(
                    bool(assigned)
                ),
            }
        )

    return rows


def method_rows(
    functions: list[FunctionInfo],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for function in functions:
        order_calls = tuple(
            call
            for call in function.calls
            if any(
                marker in call
                for marker in ORDER_CALL_MARKERS
            )
        )

        rows.append(
            {
                "layer": function.owner_layer,
                "path": function.path,
                "function": function.function,
                "line": function.line,
                "end_line": function.end_line,
                "call_count": len(function.calls),
                "return_count": len(function.returns),
                "exception_handler_count": len(
                    function.except_handlers
                ),
                "raise_count": len(function.raises),
                "order_calls": ",".join(order_calls),
                "assigned_call_count": len(
                    function.assigned_calls
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    return rows


def ownership_rows(
    execution_functions: list[FunctionInfo],
    broker_functions: list[FunctionInfo],
    edges: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    dispatcher_execute = next(
        (
            function
            for function in execution_functions
            if function.function == "execute"
        ),
        None,
    )

    dispatcher_limit = next(
        (
            function
            for function in execution_functions
            if function.function == "place_limit_order"
        ),
        None,
    )

    broker_limit = next(
        (
            function
            for function in broker_functions
            if function.function == "place_limit_order"
        ),
        None,
    )

    broker_market = next(
        (
            function
            for function in broker_functions
            if function.function == "place_market_order"
        ),
        None,
    )

    edge_limit = next(
        (
            row
            for row in edges
            if row["source_function"]
            == "place_limit_order"
        ),
        None,
    )

    rows.extend(
        [
            {
                "ownership_scope": "ORDER_SEND_DECISION",
                "candidate_layer": "EXECUTION",
                "candidate_path": (
                    dispatcher_execute.path
                    if dispatcher_execute
                    else ""
                ),
                "candidate_symbol": (
                    "ExecutionDispatcher.execute"
                ),
                "classification": (
                    "DECISION_OWNER_CANDIDATE"
                    if dispatcher_execute
                    else "UNRESOLVED"
                ),
                "evidence": (
                    "execution_entrypoint_exists"
                    if dispatcher_execute
                    else "execution_entrypoint_missing"
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            },
            {
                "ownership_scope": "LOCAL_DISPATCH_RESULT",
                "candidate_layer": "EXECUTION",
                "candidate_path": (
                    dispatcher_limit.path
                    if dispatcher_limit
                    else ""
                ),
                "candidate_symbol": (
                    "ExecutionDispatcher.place_limit_order"
                ),
                "classification": (
                    "RESULT_OWNER_CANDIDATE"
                    if dispatcher_limit
                    and edge_limit
                    and int(
                        edge_limit[
                            "broker_result_captured"
                        ]
                    )
                    == 1
                    else "UNRESOLVED"
                ),
                "evidence": (
                    "broker_result_assigned_locally"
                    if edge_limit
                    and int(
                        edge_limit[
                            "broker_result_captured"
                        ]
                    )
                    == 1
                    else "broker_result_capture_not_proven"
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            },
            {
                "ownership_scope": "BROKER_ACK_REJECT",
                "candidate_layer": "BROKER",
                "candidate_path": (
                    broker_limit.path
                    if broker_limit
                    else ""
                ),
                "candidate_symbol": "FinamOrdersClient",
                "classification": (
                    "CLASS_BOUNDARY_CANDIDATE"
                    if broker_limit and broker_market
                    else "UNRESOLVED"
                ),
                "evidence": (
                    "limit_and_market_methods_present"
                    if broker_limit and broker_market
                    else "broker_methods_incomplete"
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            },
            {
                "ownership_scope": "DOMAIN_STATUS_MAPPING",
                "candidate_layer": "UNRESOLVED",
                "candidate_path": "",
                "candidate_symbol": "",
                "classification": "UNRESOLVED",
                "evidence": (
                    "requires_return_and_exception_"
                    "mapping_review"
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            },
        ]
    )

    return rows


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


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    unresolved: list[dict[str, object]] = []
    execution_functions: list[FunctionInfo] = []
    broker_functions: list[FunctionInfo] = []

    for class_name, function_name in EXECUTION_TARGETS:
        qualified_symbol = (
            f"{class_name}.{function_name}"
        )

        try:
            execution_functions.append(
                find_function(
                    owner_layer="EXECUTION",
                    path=EXECUTION_FILE,
                    class_name=class_name,
                    function_name=function_name,
                )
            )
        except Exception as exc:
            unresolved.append(
                {
                    "scope": "EXECUTION_METHOD",
                    "symbol": qualified_symbol,
                    "reason": str(exc),
                }
            )

    for class_name, function_name in BROKER_TARGETS:
        qualified_symbol = (
            f"{class_name}.{function_name}"
        )

        try:
            broker_functions.append(
                find_function(
                    owner_layer="BROKER",
                    path=BROKER_FILE,
                    class_name=class_name,
                    function_name=function_name,
                )
            )
        except Exception as exc:
            unresolved.append(
                {
                    "scope": "BROKER_METHOD",
                    "symbol": qualified_symbol,
                    "reason": str(exc),
                }
            )

    execution_rows = method_rows(
        execution_functions
    )
    broker_rows = method_rows(
        broker_functions
    )

    edges = edge_rows(
        execution_functions,
        broker_functions,
    )

    result_rows = result_contract_rows(
        [
            *execution_functions,
            *broker_functions,
        ]
    )

    exception_contracts = exception_rows(
        [
            *execution_functions,
            *broker_functions,
        ]
    )

    ownership = ownership_rows(
        execution_functions,
        broker_functions,
        edges,
    )

    for row in ownership:
        if row["classification"] == "UNRESOLVED":
            unresolved.append(
                {
                    "scope": row["ownership_scope"],
                    "symbol": row["candidate_symbol"],
                    "reason": row["evidence"],
                }
            )

    write_tsv(
        EXECUTION_METHODS_FILE,
        (
            "layer",
            "path",
            "function",
            "line",
            "end_line",
            "call_count",
            "return_count",
            "exception_handler_count",
            "raise_count",
            "order_calls",
            "assigned_call_count",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        execution_rows,
    )

    write_tsv(
        BROKER_METHODS_FILE,
        (
            "layer",
            "path",
            "function",
            "line",
            "end_line",
            "call_count",
            "return_count",
            "exception_handler_count",
            "raise_count",
            "order_calls",
            "assigned_call_count",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        broker_rows,
    )

    write_tsv(
        EDGES_FILE,
        (
            "edge",
            "source_path",
            "source_function",
            "matched_calls",
            "assigned_result_calls",
            "reachable",
            "broker_result_captured",
        ),
        edges,
    )

    write_tsv(
        RESULTS_FILE,
        (
            "layer",
            "path",
            "function",
            "line",
            "return_index",
            "return_shape",
            "ack_markers",
            "reject_markers",
            "status_markers",
        ),
        result_rows,
    )

    write_tsv(
        EXCEPTIONS_FILE,
        (
            "layer",
            "path",
            "function",
            "line",
            "contract_type",
            "exception",
        ),
        exception_contracts,
    )

    write_tsv(
        OWNERS_FILE,
        (
            "ownership_scope",
            "candidate_layer",
            "candidate_path",
            "candidate_symbol",
            "classification",
            "evidence",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        ownership,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "symbol",
            "reason",
        ),
        unresolved,
    )

    with EVIDENCE_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "EXECUTION / BROKER RESULT OWNERSHIP V1\n"
        )
        stream.write(
            "======================================\n\n"
        )

        for function in [
            *execution_functions,
            *broker_functions,
        ]:
            stream.write("=" * 100 + "\n")
            stream.write(
                f"LAYER={function.owner_layer}\n"
                f"PATH={function.path}\n"
                f"FUNCTION={function.function}\n"
                f"LINES={function.line}-"
                f"{function.end_line}\n"
                f"CALLS={','.join(function.calls)}\n"
                f"ASSIGNED_CALLS="
                f"{','.join(function.assigned_calls)}\n"
                f"RETURNS="
                f"{','.join(function.returns)}\n"
                f"EXCEPTIONS="
                f"{','.join(function.except_handlers)}\n"
                f"RAISES="
                f"{','.join(function.raises)}\n\n"
            )
            stream.write(function.source)
            stream.write("\n\n")

    reachable_edges = sum(
        int(row["reachable"])
        for row in edges
    )

    captured_edges = sum(
        int(row["broker_result_captured"])
        for row in edges
    )

    print(
        "=== AUDIT EXECUTION BROKER "
        "RESULT OWNERSHIP V1 ==="
    )
    print(
        f"execution_method_count="
        f"{len(execution_functions)}"
    )
    print(
        f"broker_method_count="
        f"{len(broker_functions)}"
    )
    print(
        f"result_flow_edge_count={len(edges)}"
    )
    print(
        f"reachable_edge_count={reachable_edges}"
    )
    print(
        f"broker_result_captured_edge_count="
        f"{captured_edges}"
    )
    print(
        f"result_contract_count="
        f"{len(result_rows)}"
    )
    print(
        f"exception_contract_count="
        f"{len(exception_contracts)}"
    )
    print(
        f"ownership_candidate_count="
        f"{len(ownership)}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for row in edges:
        print(
            f"EDGE name={row['edge']} "
            f"reachable={row['reachable']} "
            f"result_captured="
            f"{row['broker_result_captured']} "
            f"calls={row['matched_calls']}"
        )

    for row in ownership:
        print(
            f"OWNERSHIP scope={row['ownership_scope']} "
            f"class={row['classification']} "
            f"candidate={row['candidate_symbol']} "
            f"confirmed={row['owner_confirmed']}"
        )

    print("confirmed_owner_count=0")
    print("owner_assignment_performed=0")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("execution_changed=0")
    print("broker_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "EXECUTION_BROKER_RESULT_OWNERSHIP_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
