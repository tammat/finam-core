#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

FILES = (
    (
        "EXECUTION",
        ROOT / "src/finam_core/execution/execution_dispatcher.py",
    ),
    (
        "BROKER",
        ROOT / "src/finam_core/adapters/grpc/orders_client.py",
    ),
)

TARGETS = {
    "ExecutionDispatcher.execute",
    "ExecutionDispatcher.place_limit_order",
    "FinamOrdersClient.place_limit_order",
    "FinamOrdersClient.place_market_order",
}

OUTPUT_DIR = pathlib.Path(
    "/tmp/execution_broker_domain_status_mapping_v1"
)

RETURN_FILE = OUTPUT_DIR / "return_values.tsv"
STATUS_FILE = OUTPUT_DIR / "status_assignments.tsv"
EXCEPTION_FILE = OUTPUT_DIR / "exception_mappings.tsv"
CONSUMER_FILE = OUTPUT_DIR / "broker_result_consumers.tsv"
CANDIDATE_FILE = OUTPUT_DIR / "domain_status_candidates.tsv"
EVIDENCE_FILE = OUTPUT_DIR / "evidence.txt"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

STATUS_MARKERS = {
    "ACCEPTED",
    "REJECTED",
    "FAILED",
    "ERROR",
    "TIMEOUT",
    "UNKNOWN",
    "SENT",
    "SUCCESS",
    "OK",
}

REASON_MARKERS = {
    "reason",
    "reason_code",
    "error",
    "message",
    "status",
    "result",
    "outcome",
}


@dataclass(frozen=True, slots=True)
class MethodInfo:
    layer: str
    path: str
    qualified_name: str
    line: int
    node: ast.FunctionDef | ast.AsyncFunctionDef
    source: str
    full_source: str


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return ""


def source_text(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""

    return ast.get_source_segment(source, node) or ""


def call_name(node: ast.Call) -> str:
    return dotted_name(node.func) or "<unknown>"


def load_methods(
    layer: str,
    path: pathlib.Path,
) -> list[MethodInfo]:
    if not path.is_file():
        raise RuntimeError(f"file_missing:{path}")

    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)

    result: list[MethodInfo] = []

    class Visitor(ast.NodeVisitor):
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
            qualified = ".".join(
                [*self.scope, node.name]
            )

            if qualified in TARGETS:
                result.append(
                    MethodInfo(
                        layer=layer,
                        path=str(path.relative_to(ROOT)),
                        qualified_name=qualified,
                        line=node.lineno,
                        node=node,
                        source=source_text(source, node),
                        full_source=source,
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

    Visitor().visit(tree)

    return result


def expression_shape(
    source: str,
    node: ast.AST | None,
) -> tuple[str, str]:
    if node is None:
        return "NONE", ""

    if isinstance(node, ast.Constant):
        return "CONSTANT", repr(node.value)

    if isinstance(node, ast.Name):
        return "NAME", node.id

    if isinstance(node, ast.Attribute):
        return "ATTRIBUTE", dotted_name(node)

    if isinstance(node, ast.Dict):
        # AST-координаты относятся к полному исходному файлу, тогда как
        # expression_shape может получать фрагмент метода. Поэтому ключи
        # словаря извлекаются структурно, без ast.get_source_segment.
        keys: list[str] = []

        for key in node.keys:
            if key is None:
                keys.append("**")
            elif isinstance(key, ast.Constant):
                keys.append(repr(key.value))
            elif isinstance(key, ast.Name):
                keys.append(key.id)
            elif isinstance(key, ast.Attribute):
                keys.append(dotted_name(key))
            else:
                keys.append(type(key).__name__)

        return "DICT", ",".join(keys)

    if isinstance(node, ast.Tuple):
        return "TUPLE", str(len(node.elts))

    if isinstance(node, ast.Call):
        return "CALL", call_name(node)

    return type(node).__name__.upper(), source_text(source, node)


def assignment_targets(
    source: str,
    node: ast.Assign | ast.AnnAssign,
) -> str:
    if isinstance(node, ast.Assign):
        return ",".join(
            source_text(source, target)
            for target in node.targets
        )

    return source_text(source, node.target)


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    methods: list[MethodInfo] = []

    for layer, path in FILES:
        methods.extend(load_methods(layer, path))

    unresolved: list[dict[str, object]] = []

    discovered = {
        method.qualified_name
        for method in methods
    }

    for target in sorted(TARGETS - discovered):
        unresolved.append(
            {
                "scope": "METHOD",
                "symbol": target,
                "reason": "TARGET_METHOD_NOT_FOUND",
            }
        )

    return_rows: list[dict[str, object]] = []
    status_rows: list[dict[str, object]] = []
    exception_rows: list[dict[str, object]] = []
    consumer_rows: list[dict[str, object]] = []

    for method in methods:
        method_source_lower = method.source.lower()

        for node in ast.walk(method.node):
            if isinstance(node, ast.Return):
                shape, value = expression_shape(
                    method.full_source,
                    node.value,
                )

                return_rows.append(
                    {
                        "layer": method.layer,
                        "path": method.path,
                        "method": method.qualified_name,
                        "method_line": method.line,
                        "return_line": node.lineno,
                        "return_shape": shape,
                        "return_value": value,
                    }
                )

            elif isinstance(
                node,
                (ast.Assign, ast.AnnAssign),
            ):
                value = node.value

                if value is None:
                    continue

                target_text = assignment_targets(
                    method.full_source,
                    node,
                )
                value_text = source_text(
                    method.full_source,
                    value,
                )

                normalized = (
                    f"{target_text} {value_text}"
                ).lower()

                if any(
                    marker.lower() in normalized
                    for marker in STATUS_MARKERS
                ) or any(
                    marker in normalized
                    for marker in REASON_MARKERS
                ):
                    status_rows.append(
                        {
                            "layer": method.layer,
                            "path": method.path,
                            "method": method.qualified_name,
                            "line": node.lineno,
                            "target": target_text,
                            "value": value_text,
                        }
                    )

                call_node = value

                if isinstance(call_node, ast.Await):
                    call_node = call_node.value

                if isinstance(call_node, ast.Call):
                    call = call_name(call_node)

                    if (
                        "orders_client." in call
                        or "place_limit_order" in call
                        or "place_market_order" in call
                    ):
                        consumer_rows.append(
                            {
                                "layer": method.layer,
                                "path": method.path,
                                "method": method.qualified_name,
                                "line": node.lineno,
                                "result_target": target_text,
                                "broker_call": call,
                                "result_consumed": 1,
                            }
                        )

            elif isinstance(node, ast.ExceptHandler):
                exception_type = (
                    dotted_name(node.type)
                    if node.type is not None
                    else "BARE_EXCEPT"
                )

                body_text = "\n".join(
                    source_text(method.full_source, item)
                    for item in node.body
                )

                mapping_hits = sorted(
                    marker
                    for marker in STATUS_MARKERS
                    if marker.lower()
                    in body_text.lower()
                )

                exception_rows.append(
                    {
                        "layer": method.layer,
                        "path": method.path,
                        "method": method.qualified_name,
                        "line": node.lineno,
                        "exception_type": exception_type,
                        "mapping_markers": ",".join(
                            mapping_hits
                        ),
                        "handler_body": body_text,
                    }
                )

        if not any(
            row["method"] == method.qualified_name
            for row in return_rows
        ):
            unresolved.append(
                {
                    "scope": "RETURN_CONTRACT",
                    "symbol": method.qualified_name,
                    "reason": "NO_RETURN_STATEMENT_FOUND",
                }
            )

    candidate_rows: list[dict[str, object]] = []

    dispatcher_status_mapping = any(
        row["method"].startswith(
            "ExecutionDispatcher."
        )
        for row in status_rows
    )

    broker_status_mapping = any(
        row["method"].startswith(
            "FinamOrdersClient."
        )
        for row in status_rows
    )

    dispatcher_exception_mapping = any(
        row["method"].startswith(
            "ExecutionDispatcher."
        )
        and row["mapping_markers"]
        for row in exception_rows
    )

    broker_exception_mapping = any(
        row["method"].startswith(
            "FinamOrdersClient."
        )
        and row["mapping_markers"]
        for row in exception_rows
    )

    if dispatcher_status_mapping or dispatcher_exception_mapping:
        candidate_rows.append(
            {
                "scope": "DOMAIN_STATUS_MAPPING",
                "candidate_layer": "EXECUTION",
                "candidate_symbol": "ExecutionDispatcher",
                "classification": (
                    "DOMAIN_STATUS_OWNER_CANDIDATE"
                ),
                "status_mapping_found": int(
                    dispatcher_status_mapping
                ),
                "exception_mapping_found": int(
                    dispatcher_exception_mapping
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    if broker_status_mapping or broker_exception_mapping:
        candidate_rows.append(
            {
                "scope": "DOMAIN_STATUS_MAPPING",
                "candidate_layer": "BROKER",
                "candidate_symbol": "FinamOrdersClient",
                "classification": (
                    "BROKER_STATUS_OWNER_CANDIDATE"
                ),
                "status_mapping_found": int(
                    broker_status_mapping
                ),
                "exception_mapping_found": int(
                    broker_exception_mapping
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    if not candidate_rows:
        unresolved.append(
            {
                "scope": "DOMAIN_STATUS_MAPPING",
                "symbol": "",
                "reason": (
                    "NO_EXPLICIT_STATUS_OR_EXCEPTION_MAPPING_FOUND"
                ),
            }
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

    write_tsv(
        RETURN_FILE,
        (
            "layer",
            "path",
            "method",
            "method_line",
            "return_line",
            "return_shape",
            "return_value",
        ),
        return_rows,
    )

    write_tsv(
        STATUS_FILE,
        (
            "layer",
            "path",
            "method",
            "line",
            "target",
            "value",
        ),
        status_rows,
    )

    write_tsv(
        EXCEPTION_FILE,
        (
            "layer",
            "path",
            "method",
            "line",
            "exception_type",
            "mapping_markers",
            "handler_body",
        ),
        exception_rows,
    )

    write_tsv(
        CONSUMER_FILE,
        (
            "layer",
            "path",
            "method",
            "line",
            "result_target",
            "broker_call",
            "result_consumed",
        ),
        consumer_rows,
    )

    write_tsv(
        CANDIDATE_FILE,
        (
            "scope",
            "candidate_layer",
            "candidate_symbol",
            "classification",
            "status_mapping_found",
            "exception_mapping_found",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        candidate_rows,
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
            "EXECUTION BROKER DOMAIN STATUS MAPPING V1\n"
        )
        stream.write(
            "=========================================\n\n"
        )

        for row in return_rows:
            stream.write(
                f"RETURN method={row['method']} "
                f"line={row['return_line']} "
                f"shape={row['return_shape']} "
                f"value={row['return_value']}\n"
            )

        stream.write("\n")

        for row in status_rows:
            stream.write(
                f"STATUS method={row['method']} "
                f"line={row['line']} "
                f"target={row['target']} "
                f"value={row['value']}\n"
            )

        stream.write("\n")

        for row in exception_rows:
            stream.write(
                f"EXCEPTION method={row['method']} "
                f"line={row['line']} "
                f"type={row['exception_type']} "
                f"mappings={row['mapping_markers']}\n"
            )

    print(
        "=== AUDIT EXECUTION BROKER "
        "DOMAIN STATUS MAPPING V1 ==="
    )
    print(f"target_method_count={len(methods)}")
    print(f"return_value_count={len(return_rows)}")
    print(
        f"status_assignment_count={len(status_rows)}"
    )
    print(
        f"exception_mapping_count="
        f"{len(exception_rows)}"
    )
    print(
        f"broker_result_consumer_count="
        f"{len(consumer_rows)}"
    )
    print(
        f"domain_status_candidate_count="
        f"{len(candidate_rows)}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for row in candidate_rows:
        print(
            f"CANDIDATE scope={row['scope']} "
            f"layer={row['candidate_layer']} "
            f"symbol={row['candidate_symbol']} "
            f"status_mapping="
            f"{row['status_mapping_found']} "
            f"exception_mapping="
            f"{row['exception_mapping_found']}"
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
        "EXECUTION_BROKER_DOMAIN_STATUS_MAPPING_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
