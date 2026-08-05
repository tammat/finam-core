#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from collections import defaultdict
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

SEMANTIC_FILE = pathlib.Path(
    "/tmp/edge_semantic_classification_v1/"
    "authoritative_decision_candidates.tsv"
)

OUT = pathlib.Path(
    "/tmp/edge_decision_boundary_v1"
)

CANDIDATES_FILE = OUT / "authoritative_candidates.tsv"
CALLS_FILE = OUT / "candidate_call_sites.tsv"
BINDINGS_FILE = OUT / "candidate_result_bindings.tsv"
CONSUMERS_FILE = OUT / "result_consumers.tsv"
CANDIDATE_EDGES_FILE = OUT / "candidate_to_candidate_edges.tsv"
DOWNSTREAM_FILE = OUT / "downstream_boundary_edges.tsv"
SUMMARY_FILE = OUT / "boundary_summary.tsv"
EVIDENCE_FILE = OUT / "evidence.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

SOURCE_ROOTS = (
    ROOT / "src/finam_core",
    ROOT / "core",
    ROOT / "strategy",
    ROOT / "risk",
)

EXPECTED_IDENTITIES = {
    (
        "src/finam_core/analytics/directional_edge_guard.py",
        "DirectionalEdgeGuard.decide",
    ),
    (
        "src/finam_core/analytics/statistical_validation_decision.py",
        "StatisticalValidationDecisionEngine.decide",
    ),
    (
        "src/finam_core/analytics/session_edge_guard.py",
        "SessionEdgeGuard.decide",
    ),
}

DOWNSTREAM_MARKERS = (
    "risk",
    "runtime",
    "allow",
    "allowed",
    "approve",
    "approved",
    "reject",
    "rejected",
    "block",
    "blocked",
    "decision",
    "gate",
    "execute",
)

DECISION_FIELD_MARKERS = (
    "allowed",
    "allow",
    "approved",
    "approve",
    "decision",
    "status",
    "reason",
    "rejected",
    "blocked",
    "eligible",
)

RUNTIME_ENTRYPOINTS = {
    "_on_quote_impl",
    "_record_live_quote_to_storage",
    "_process_br_closed_bar_for_paper_signal",
    "_process_ng_m1_closed_bar_for_paper_signal",
    "_process_equity_closed_bar_for_paper_signal",
    "_execute_br_signal_in_paper",
}

FIELDS_CANDIDATE = (
    "path",
    "class_name",
    "function",
    "qualified_name",
    "line",
    "semantic_classification",
)

FIELDS_CALL = (
    "candidate_path",
    "candidate_symbol",
    "caller_path",
    "caller_class",
    "caller_function",
    "caller_symbol",
    "caller_line",
    "call_line",
    "receiver",
    "call",
    "result_target",
    "call_source",
)

FIELDS_BINDING = (
    "candidate_path",
    "candidate_symbol",
    "caller_path",
    "caller_symbol",
    "call_line",
    "result_target",
    "binding_type",
)

FIELDS_CONSUMER = (
    "candidate_symbol",
    "result_target",
    "consumer_path",
    "consumer_symbol",
    "consumer_line",
    "usage_type",
    "usage_source",
)

FIELDS_EDGE = (
    "source_candidate",
    "target_candidate",
    "caller_path",
    "caller_symbol",
    "evidence",
)

FIELDS_DOWNSTREAM = (
    "candidate_symbol",
    "caller_path",
    "caller_symbol",
    "downstream_call",
    "downstream_line",
    "classification",
)

FIELDS_SUMMARY = (
    "candidate_path",
    "candidate_symbol",
    "direct_call_count",
    "bound_result_count",
    "result_consumer_count",
    "candidate_out_edge_count",
    "candidate_in_edge_count",
    "downstream_boundary_count",
    "runtime_reachable_call_count",
    "classification",
    "owner_confirmed",
    "runtime_instrumentation",
)


@dataclass(frozen=True, slots=True)
class Candidate:
    path: str
    class_name: str
    function: str
    symbol: str
    line: int
    semantic_classification: str


@dataclass(frozen=True, slots=True)
class FunctionContext:
    path: str
    class_name: str
    function_name: str
    symbol: str
    line: int
    node: ast.FunctionDef | ast.AsyncFunctionDef
    source: str


def read_tsv(
    path: pathlib.Path,
) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(
            f"source_file_missing:{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        return [
            {
                key: str(value or "").strip()
                for key, value in row.items()
            }
            for row in csv.DictReader(
                stream,
                delimiter="\t",
            )
        ]


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
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def dotted_name(
    node: ast.AST | None,
) -> str:
    if node is None:
        return ""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return (
            f"{parent}.{node.attr}"
            if parent
            else node.attr
        )

    if isinstance(node, ast.Subscript):
        return dotted_name(node.value)

    return ""


def source_text(
    source: str,
    node: ast.AST | None,
) -> str:
    if node is None:
        return ""

    try:
        return (
            ast.get_source_segment(
                source,
                node,
            )
            or ""
        )
    except (IndexError, ValueError):
        return ""


def assignment_targets(
    node: ast.Assign | ast.AnnAssign,
) -> list[str]:
    targets: list[ast.AST]

    if isinstance(node, ast.Assign):
        targets = list(node.targets)
    else:
        targets = [node.target]

    result: list[str] = []

    for target in targets:
        name = dotted_name(target)

        if name:
            result.append(name)

    return result


def load_candidates() -> list[Candidate]:
    rows = read_tsv(SEMANTIC_FILE)

    candidates = [
        Candidate(
            path=row["path"],
            class_name=row["class_name"],
            function=row["function"],
            symbol=row["qualified_name"],
            line=int(row["line"] or 0),
            semantic_classification=row[
                "semantic_classification"
            ],
        )
        for row in rows
        if row["semantic_classification"]
        == "AUTHORITATIVE_EDGE_DECISION_CANDIDATE"
    ]

    actual = {
        (candidate.path, candidate.symbol)
        for candidate in candidates
    }

    if actual != EXPECTED_IDENTITIES:
        missing = sorted(
            EXPECTED_IDENTITIES - actual
        )
        unexpected = sorted(
            actual - EXPECTED_IDENTITIES
        )

        raise RuntimeError(
            "authoritative_candidate_identity_mismatch:"
            f"missing={missing}:"
            f"unexpected={unexpected}"
        )

    return sorted(
        candidates,
        key=lambda item: (
            item.path,
            item.symbol,
        ),
    )


def discover_files() -> list[pathlib.Path]:
    result: set[pathlib.Path] = set()

    for root in SOURCE_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue

            result.add(path.resolve())

    return sorted(result)


def discover_functions(
    path: pathlib.Path,
) -> list[FunctionContext]:
    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)
    relative = str(
        path.relative_to(ROOT)
    )

    result: list[FunctionContext] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.classes: list[str] = []
            self.functions: list[str] = []

        def visit_ClassDef(
            self,
            node: ast.ClassDef,
        ) -> None:
            self.classes.append(node.name)
            self.generic_visit(node)
            self.classes.pop()

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

        def _visit_function(
            self,
            node: ast.FunctionDef
            | ast.AsyncFunctionDef,
        ) -> None:
            symbol = ".".join(
                [
                    *self.classes,
                    *self.functions,
                    node.name,
                ]
            )

            result.append(
                FunctionContext(
                    path=relative,
                    class_name=".".join(
                        self.classes
                    ),
                    function_name=node.name,
                    symbol=symbol,
                    line=node.lineno,
                    node=node,
                    source=source,
                )
            )

            self.functions.append(
                node.name
            )
            self.generic_visit(node)
            self.functions.pop()

    Visitor().visit(tree)

    return result


def receiver_name(
    call_name: str,
) -> str:
    if "." not in call_name:
        return ""

    return call_name.rsplit(".", 1)[0]


def terminal_name(
    call_name: str,
) -> str:
    return call_name.rsplit(".", 1)[-1]


def main() -> int:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidates = load_candidates()

    candidate_by_method: dict[
        str,
        list[Candidate],
    ] = defaultdict(list)

    for candidate in candidates:
        candidate_by_method[
            candidate.function
        ].append(candidate)

    functions: list[FunctionContext] = []

    for path in discover_files():
        try:
            functions.extend(
                discover_functions(path)
            )
        except (
            OSError,
            SyntaxError,
        ):
            continue

    call_rows: list[
        dict[str, object]
    ] = []
    binding_rows: list[
        dict[str, object]
    ] = []
    consumer_rows: list[
        dict[str, object]
    ] = []
    candidate_edges: list[
        dict[str, object]
    ] = []
    downstream_rows: list[
        dict[str, object]
    ] = []
    unresolved: list[
        dict[str, object]
    ] = []

    function_calls: dict[
        str,
        set[str],
    ] = defaultdict(set)

    candidate_callers: dict[
        str,
        set[str],
    ] = defaultdict(set)

    result_bindings: dict[
        tuple[str, str],
        list[
            tuple[
                Candidate,
                FunctionContext,
                int,
            ]
        ],
    ] = defaultdict(list)

    for function in functions:
        candidate_calls_in_function: list[
            tuple[
                Candidate,
                int,
                str,
                str,
                str,
            ]
        ] = []

        for node in ast.walk(
            function.node
        ):
            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            call_name = dotted_name(
                node.func
            )
            method = terminal_name(
                call_name
            )

            if method:
                function_calls[
                    function.function_name
                ].add(method)

            method_candidates = (
                candidate_by_method.get(
                    method,
                    [],
                )
            )

            if not method_candidates:
                continue

            # При одинаковом имени decide разрешаем
            # кандидата по локальному файлу определения,
            # имени receiver либо уникальному class token.
            receiver = receiver_name(
                call_name
            ).lower()

            matched: list[Candidate] = []

            for candidate in method_candidates:
                class_token = (
                    candidate.class_name
                    .rsplit(".", 1)[-1]
                    .lower()
                )

                path_token = (
                    pathlib.Path(
                        candidate.path
                    )
                    .stem.lower()
                )

                if (
                    class_token
                    and class_token
                    in receiver
                ):
                    matched.append(
                        candidate
                    )
                elif (
                    path_token
                    and path_token
                    in receiver
                ):
                    matched.append(
                        candidate
                    )

            if not matched:
                if len(method_candidates) == 1:
                    matched = list(
                        method_candidates
                    )
                else:
                    unresolved.append(
                        {
                            "scope": "CALL_BINDING",
                            "symbol": call_name,
                            "reason": (
                                "AMBIGUOUS_DECIDE_RECEIVER"
                            ),
                        }
                    )
                    continue

            result_target = ""

            parent_assignment = None

            for parent in ast.walk(
                function.node
            ):
                if not isinstance(
                    parent,
                    (
                        ast.Assign,
                        ast.AnnAssign,
                    ),
                ):
                    continue

                if parent.value is node:
                    parent_assignment = parent
                    break

            if parent_assignment:
                targets = assignment_targets(
                    parent_assignment
                )
                result_target = (
                    targets[0]
                    if targets
                    else ""
                )

            for candidate in matched:
                call_rows.append(
                    {
                        "candidate_path": (
                            candidate.path
                        ),
                        "candidate_symbol": (
                            candidate.symbol
                        ),
                        "caller_path": (
                            function.path
                        ),
                        "caller_class": (
                            function.class_name
                        ),
                        "caller_function": (
                            function.function_name
                        ),
                        "caller_symbol": (
                            function.symbol
                        ),
                        "caller_line": (
                            function.line
                        ),
                        "call_line": (
                            node.lineno
                        ),
                        "receiver": receiver_name(
                            call_name
                        ),
                        "call": call_name,
                        "result_target": (
                            result_target
                        ),
                        "call_source": (
                            source_text(
                                function.source,
                                node,
                            )
                        ),
                    }
                )

                candidate_callers[
                    candidate.symbol
                ].add(function.symbol)

                candidate_calls_in_function.append(
                    (
                        candidate,
                        node.lineno,
                        result_target,
                        call_name,
                        source_text(
                            function.source,
                            node,
                        ),
                    )
                )

                if result_target:
                    binding_rows.append(
                        {
                            "candidate_path": (
                                candidate.path
                            ),
                            "candidate_symbol": (
                                candidate.symbol
                            ),
                            "caller_path": (
                                function.path
                            ),
                            "caller_symbol": (
                                function.symbol
                            ),
                            "call_line": (
                                node.lineno
                            ),
                            "result_target": (
                                result_target
                            ),
                            "binding_type": (
                                "ASSIGNED_CALL_RESULT"
                            ),
                        }
                    )

                    result_bindings[
                        (
                            function.symbol,
                            result_target,
                        )
                    ].append(
                        (
                            candidate,
                            function,
                            node.lineno,
                        )
                    )

        # Проверяем прямой порядок вызовов кандидатов
        # внутри одной функции.
        ordered = sorted(
            candidate_calls_in_function,
            key=lambda item: item[1],
        )

        for index, source_call in enumerate(
            ordered
        ):
            source_candidate = (
                source_call[0]
            )

            for target_call in ordered[
                index + 1:
            ]:
                target_candidate = (
                    target_call[0]
                )

                if (
                    source_candidate.symbol
                    == target_candidate.symbol
                ):
                    continue

                evidence = (
                    "SAME_CALLER_ORDER:"
                    f"{source_call[1]}"
                    f"->{target_call[1]}"
                )

                candidate_edges.append(
                    {
                        "source_candidate": (
                            source_candidate.symbol
                        ),
                        "target_candidate": (
                            target_candidate.symbol
                        ),
                        "caller_path": (
                            function.path
                        ),
                        "caller_symbol": (
                            function.symbol
                        ),
                        "evidence": evidence,
                    }
                )

        # Проверяем использование результатов.
        for (
            candidate,
            call_line,
            result_target,
            _call_name,
            _call_source,
        ) in candidate_calls_in_function:
            if not result_target:
                continue

            target_terminal = (
                result_target
                .rsplit(".", 1)[-1]
            )

            for node in ast.walk(
                function.node
            ):
                if getattr(
                    node,
                    "lineno",
                    0,
                ) <= call_line:
                    continue

                usage_source = source_text(
                    function.source,
                    node,
                )

                if not usage_source:
                    continue

                if (
                    result_target
                    not in usage_source
                    and target_terminal
                    not in usage_source
                ):
                    continue

                usage_type = (
                    "CONDITIONAL"
                    if isinstance(
                        node,
                        (
                            ast.If,
                            ast.IfExp,
                            ast.While,
                        ),
                    )
                    else "EXPRESSION"
                )

                consumer_rows.append(
                    {
                        "candidate_symbol": (
                            candidate.symbol
                        ),
                        "result_target": (
                            result_target
                        ),
                        "consumer_path": (
                            function.path
                        ),
                        "consumer_symbol": (
                            function.symbol
                        ),
                        "consumer_line": (
                            getattr(
                                node,
                                "lineno",
                                0,
                            )
                        ),
                        "usage_type": (
                            usage_type
                        ),
                        "usage_source": (
                            usage_source
                        ),
                    }
                )

            # Ищем последующие downstream-вызовы
            # в том же caller.
            for node in ast.walk(
                function.node
            ):
                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue

                if node.lineno <= call_line:
                    continue

                downstream_call = (
                    dotted_name(
                        node.func
                    )
                )
                lower = (
                    downstream_call.lower()
                )

                if not any(
                    marker in lower
                    for marker
                    in DOWNSTREAM_MARKERS
                ):
                    continue

                downstream_rows.append(
                    {
                        "candidate_symbol": (
                            candidate.symbol
                        ),
                        "caller_path": (
                            function.path
                        ),
                        "caller_symbol": (
                            function.symbol
                        ),
                        "downstream_call": (
                            downstream_call
                        ),
                        "downstream_line": (
                            node.lineno
                        ),
                        "classification": (
                            "DOWNSTREAM_DECISION_BOUNDARY_CANDIDATE"
                        ),
                    }
                )

    reverse_graph: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for caller, callees in (
        function_calls.items()
    ):
        for callee in callees:
            reverse_graph[
                callee
            ].add(caller)

    def runtime_reachable(
        function_name: str,
    ) -> bool:
        queue = [function_name]
        visited: set[str] = set()

        while queue:
            current = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            if (
                current
                in RUNTIME_ENTRYPOINTS
            ):
                return True

            queue.extend(
                sorted(
                    reverse_graph.get(
                        current,
                        set(),
                    )
                )
            )

        return False

    summary_rows: list[
        dict[str, object]
    ] = []

    for candidate in candidates:
        calls = [
            row
            for row in call_rows
            if row[
                "candidate_symbol"
            ] == candidate.symbol
        ]

        bindings = [
            row
            for row in binding_rows
            if row[
                "candidate_symbol"
            ] == candidate.symbol
        ]

        consumers = [
            row
            for row in consumer_rows
            if row[
                "candidate_symbol"
            ] == candidate.symbol
        ]

        out_edges = [
            row
            for row in candidate_edges
            if row[
                "source_candidate"
            ] == candidate.symbol
        ]

        in_edges = [
            row
            for row in candidate_edges
            if row[
                "target_candidate"
            ] == candidate.symbol
        ]

        downstream = [
            row
            for row in downstream_rows
            if row[
                "candidate_symbol"
            ] == candidate.symbol
        ]

        runtime_calls = sum(
            runtime_reachable(
                str(
                    row[
                        "caller_function"
                    ]
                )
            )
            for row in calls
        )

        if (
            out_edges
            and not in_edges
        ):
            classification = (
                "UPSTREAM_PARTIAL_EDGE_BOUNDARY"
            )
        elif (
            in_edges
            and out_edges
        ):
            classification = (
                "INTERMEDIATE_EDGE_BOUNDARY"
            )
        elif (
            in_edges
            and downstream
        ):
            classification = (
                "FINAL_EDGE_BOUNDARY_CANDIDATE"
            )
        elif (
            downstream
            and consumers
        ):
            classification = (
                "INDEPENDENT_EDGE_BOUNDARY_CANDIDATE"
            )
        elif calls:
            classification = (
                "CALLED_WITHOUT_BOUNDARY_PROOF"
            )
        else:
            classification = (
                "NO_CALL_SITE_DISCOVERED"
            )

        summary_rows.append(
            {
                "candidate_path": (
                    candidate.path
                ),
                "candidate_symbol": (
                    candidate.symbol
                ),
                "direct_call_count": (
                    len(calls)
                ),
                "bound_result_count": (
                    len(bindings)
                ),
                "result_consumer_count": (
                    len(consumers)
                ),
                "candidate_out_edge_count": (
                    len(out_edges)
                ),
                "candidate_in_edge_count": (
                    len(in_edges)
                ),
                "downstream_boundary_count": (
                    len(downstream)
                ),
                "runtime_reachable_call_count": (
                    runtime_calls
                ),
                "classification": (
                    classification
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    write_tsv(
        CANDIDATES_FILE,
        FIELDS_CANDIDATE,
        [
            {
                "path": candidate.path,
                "class_name": (
                    candidate.class_name
                ),
                "function": (
                    candidate.function
                ),
                "qualified_name": (
                    candidate.symbol
                ),
                "line": candidate.line,
                "semantic_classification": (
                    candidate
                    .semantic_classification
                ),
            }
            for candidate in candidates
        ],
    )

    write_tsv(
        CALLS_FILE,
        FIELDS_CALL,
        call_rows,
    )

    write_tsv(
        BINDINGS_FILE,
        FIELDS_BINDING,
        binding_rows,
    )

    write_tsv(
        CONSUMERS_FILE,
        FIELDS_CONSUMER,
        consumer_rows,
    )

    write_tsv(
        CANDIDATE_EDGES_FILE,
        FIELDS_EDGE,
        candidate_edges,
    )

    write_tsv(
        DOWNSTREAM_FILE,
        FIELDS_DOWNSTREAM,
        downstream_rows,
    )

    write_tsv(
        SUMMARY_FILE,
        FIELDS_SUMMARY,
        summary_rows,
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
            "EDGE DECISION BOUNDARY V1\n"
        )
        stream.write(
            "=========================\n\n"
        )

        for row in summary_rows:
            stream.write(
                "BOUNDARY "
                f"symbol="
                f"{row['candidate_symbol']} "
                f"calls="
                f"{row['direct_call_count']} "
                f"bindings="
                f"{row['bound_result_count']} "
                f"consumers="
                f"{row['result_consumer_count']} "
                f"out_edges="
                f"{row['candidate_out_edge_count']} "
                f"in_edges="
                f"{row['candidate_in_edge_count']} "
                f"downstream="
                f"{row['downstream_boundary_count']} "
                f"runtime_calls="
                f"{row['runtime_reachable_call_count']} "
                f"class="
                f"{row['classification']}\n"
            )

    print(
        "=== AUDIT EDGE DECISION "
        "BOUNDARY V1 ==="
    )
    print(
        f"authoritative_candidate_count="
        f"{len(candidates)}"
    )
    print(
        f"candidate_call_site_count="
        f"{len(call_rows)}"
    )
    print(
        f"candidate_result_binding_count="
        f"{len(binding_rows)}"
    )
    print(
        f"result_consumer_count="
        f"{len(consumer_rows)}"
    )
    print(
        f"candidate_to_candidate_edge_count="
        f"{len(candidate_edges)}"
    )
    print(
        f"downstream_boundary_edge_count="
        f"{len(downstream_rows)}"
    )
    print(
        f"unresolved_count="
        f"{len(unresolved)}"
    )

    for row in summary_rows:
        print(
            "BOUNDARY "
            f"symbol={row['candidate_symbol']} "
            f"calls={row['direct_call_count']} "
            f"bindings={row['bound_result_count']} "
            f"consumers={row['result_consumer_count']} "
            f"out_edges="
            f"{row['candidate_out_edge_count']} "
            f"in_edges="
            f"{row['candidate_in_edge_count']} "
            f"downstream="
            f"{row['downstream_boundary_count']} "
            f"runtime_calls="
            f"{row['runtime_reachable_call_count']} "
            f"class={row['classification']}"
        )

    print("confirmed_owner_count=0")
    print("owner_assignment_performed=0")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("broker_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "EDGE_DECISION_BOUNDARY_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
