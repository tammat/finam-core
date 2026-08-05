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
    "/tmp/edge_decision_boundary_qualified_binding_v2"
)

CANDIDATES_FILE = OUT / "candidate_identities.tsv"
IMPORTS_FILE = OUT / "import_aliases.tsv"
CONSTRUCTORS_FILE = OUT / "constructor_bindings.tsv"
ATTRIBUTES_FILE = OUT / "attribute_bindings.tsv"
LOCALS_FILE = OUT / "local_bindings.tsv"
CALLS_FILE = OUT / "qualified_call_sites.tsv"
AMBIGUOUS_FILE = OUT / "remaining_ambiguous_calls.tsv"
SUMMARY_FILE = OUT / "candidate_summary.tsv"
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
        "DirectionalEdgeGuard",
        "decide",
        "DirectionalEdgeGuard.decide",
    ),
    (
        "src/finam_core/analytics/statistical_validation_decision.py",
        "StatisticalValidationDecisionEngine",
        "decide",
        "StatisticalValidationDecisionEngine.decide",
    ),
    (
        "src/finam_core/analytics/session_edge_guard.py",
        "SessionEdgeGuard",
        "decide",
        "SessionEdgeGuard.decide",
    ),
}

RUNTIME_ENTRYPOINTS = {
    "_on_quote_impl",
    "_record_live_quote_to_storage",
    "_process_br_closed_bar_for_paper_signal",
    "_process_ng_m1_closed_bar_for_paper_signal",
    "_process_equity_closed_bar_for_paper_signal",
    "_execute_br_signal_in_paper",
}


@dataclass(frozen=True, slots=True)
class Candidate:
    path: str
    class_name: str
    method: str
    symbol: str


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
        value = dotted_name(target)

        if value:
            result.append(value)

    return result


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


def load_candidates() -> list[Candidate]:
    rows = read_tsv(SEMANTIC_FILE)

    candidates = [
        Candidate(
            path=row["path"],
            class_name=row["class_name"],
            method=row["function"],
            symbol=row["qualified_name"],
        )
        for row in rows
        if row["semantic_classification"]
        == "AUTHORITATIVE_EDGE_DECISION_CANDIDATE"
    ]

    actual = {
        (
            candidate.path,
            candidate.class_name,
            candidate.method,
            candidate.symbol,
        )
        for candidate in candidates
    }

    if actual != EXPECTED_IDENTITIES:
        raise RuntimeError(
            "candidate_identity_mismatch:"
            f"missing={sorted(EXPECTED_IDENTITIES - actual)}:"
            f"unexpected={sorted(actual - EXPECTED_IDENTITIES)}"
        )

    return candidates


def constructor_class(
    node: ast.AST | None,
    import_aliases: dict[str, str],
) -> str:
    if not isinstance(node, ast.Call):
        return ""

    constructor = dotted_name(node.func)
    terminal = constructor.rsplit(".", 1)[-1]

    return import_aliases.get(
        terminal,
        terminal,
    )


def main() -> int:
    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    candidates = load_candidates()

    candidate_classes = {
        candidate.class_name
        for candidate in candidates
    }

    candidate_by_class_method = {
        (
            candidate.class_name,
            candidate.method,
        ): candidate
        for candidate in candidates
    }

    candidate_rows = [
        {
            "path": candidate.path,
            "class_name": candidate.class_name,
            "method": candidate.method,
            "candidate_symbol": candidate.symbol,
        }
        for candidate in candidates
    ]

    import_rows: list[dict[str, object]] = []
    constructor_rows: list[dict[str, object]] = []
    attribute_rows: list[dict[str, object]] = []
    local_rows: list[dict[str, object]] = []
    call_rows: list[dict[str, object]] = []
    ambiguous_rows: list[dict[str, object]] = []

    call_graph: dict[str, set[str]] = defaultdict(set)

    for path in discover_files():
        relative = str(
            path.relative_to(ROOT)
        )
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        import_aliases: dict[str, str] = {}

        for node in tree.body:
            if isinstance(
                node,
                ast.ImportFrom,
            ):
                for alias in node.names:
                    local_name = (
                        alias.asname
                        or alias.name
                    )
                    imported_name = (
                        alias.name.rsplit(
                            ".",
                            1,
                        )[-1]
                    )
                    import_aliases[
                        local_name
                    ] = imported_name

                    import_rows.append(
                        {
                            "path": relative,
                            "line": node.lineno,
                            "local_name": (
                                local_name
                            ),
                            "imported_name": (
                                imported_name
                            ),
                            "module": (
                                node.module or ""
                            ),
                        }
                    )

            elif isinstance(
                node,
                ast.Import,
            ):
                for alias in node.names:
                    local_name = (
                        alias.asname
                        or alias.name
                    )
                    imported_name = (
                        alias.name.rsplit(
                            ".",
                            1,
                        )[-1]
                    )
                    import_aliases[
                        local_name
                    ] = imported_name

                    import_rows.append(
                        {
                            "path": relative,
                            "line": node.lineno,
                            "local_name": (
                                local_name
                            ),
                            "imported_name": (
                                imported_name
                            ),
                            "module": alias.name,
                        }
                    )

        class_attribute_bindings: dict[
            str,
            dict[str, str],
        ] = defaultdict(dict)

        class_stack: list[str] = []

        class AttributeBindingVisitor(
            ast.NodeVisitor
        ):
            def visit_ClassDef(
                self,
                node: ast.ClassDef,
            ) -> None:
                class_stack.append(
                    node.name
                )
                self.generic_visit(node)
                class_stack.pop()

            def visit_Assign(
                self,
                node: ast.Assign,
            ) -> None:
                self._handle(node)
                self.generic_visit(node)

            def visit_AnnAssign(
                self,
                node: ast.AnnAssign,
            ) -> None:
                self._handle(node)
                self.generic_visit(node)

            def _handle(
                self,
                node: ast.Assign
                | ast.AnnAssign,
            ) -> None:
                if (
                    not class_stack
                    or node.value is None
                ):
                    return

                bound_class = constructor_class(
                    node.value,
                    import_aliases,
                )

                if (
                    not bound_class
                    and isinstance(
                        node.value,
                        (
                            ast.Name,
                            ast.Attribute,
                        ),
                    )
                ):
                    source_name = dotted_name(
                        node.value
                    )
                    source_receiver = (
                        source_name.rsplit(
                            ".",
                            1,
                        )[-1]
                    )
                    bound_class = (
                        class_attribute_bindings[
                            class_stack[-1]
                        ].get(
                            source_receiver,
                            "",
                        )
                    )

                if (
                    bound_class
                    not in candidate_classes
                ):
                    return

                for target in assignment_targets(
                    node
                ):
                    receiver = (
                        target.rsplit(
                            ".",
                            1,
                        )[-1]
                    )

                    class_attribute_bindings[
                        class_stack[-1]
                    ][receiver] = (
                        bound_class
                    )

                    attribute_rows.append(
                        {
                            "path": relative,
                            "owner_class": (
                                class_stack[-1]
                            ),
                            "line": (
                                node.lineno
                            ),
                            "target": target,
                            "receiver": (
                                receiver
                            ),
                            "bound_class": (
                                bound_class
                            ),
                            "source": (
                                source_text(
                                    source,
                                    node.value,
                                )
                            ),
                        }
                    )

        AttributeBindingVisitor().visit(
            tree
        )

        class_stack = []
        function_stack: list[str] = []

        class CallVisitor(ast.NodeVisitor):
            def visit_ClassDef(
                self,
                node: ast.ClassDef,
            ) -> None:
                class_stack.append(
                    node.name
                )
                self.generic_visit(node)
                class_stack.pop()

            def visit_FunctionDef(
                self,
                node: ast.FunctionDef,
            ) -> None:
                self._handle_function(
                    node
                )

            def visit_AsyncFunctionDef(
                self,
                node: ast.AsyncFunctionDef,
            ) -> None:
                self._handle_function(
                    node
                )

            def _handle_function(
                self,
                node: ast.FunctionDef
                | ast.AsyncFunctionDef,
            ) -> None:
                caller_symbol = ".".join(
                    [
                        *class_stack,
                        *function_stack,
                        node.name,
                    ]
                )

                owner_class = (
                    class_stack[-1]
                    if class_stack
                    else ""
                )

                local_bindings = dict(
                    class_attribute_bindings.get(
                        owner_class,
                        {},
                    )
                )

                function_stack.append(
                    node.name
                )

                for child in ast.walk(
                    node
                ):
                    if not isinstance(
                        child,
                        (
                            ast.Assign,
                            ast.AnnAssign,
                        ),
                    ):
                        continue

                    if child.value is None:
                        continue

                    bound_class = constructor_class(
                        child.value,
                        import_aliases,
                    )

                    binding_type = (
                        "LOCAL_CONSTRUCTOR"
                    )

                    if (
                        not bound_class
                        and isinstance(
                            child.value,
                            (
                                ast.Name,
                                ast.Attribute,
                            ),
                        )
                    ):
                        source_name = (
                            dotted_name(
                                child.value
                            )
                        )
                        source_receiver = (
                            source_name.rsplit(
                                ".",
                                1,
                            )[-1]
                        )
                        bound_class = (
                            local_bindings.get(
                                source_receiver,
                                "",
                            )
                        )
                        binding_type = (
                            "LOCAL_ALIAS"
                        )

                    if (
                        bound_class
                        not in candidate_classes
                    ):
                        continue

                    for target in (
                        assignment_targets(
                            child
                        )
                    ):
                        receiver = (
                            target.rsplit(
                                ".",
                                1,
                            )[-1]
                        )
                        local_bindings[
                            receiver
                        ] = bound_class

                        local_rows.append(
                            {
                                "path": (
                                    relative
                                ),
                                "caller_symbol": (
                                    caller_symbol
                                ),
                                "line": (
                                    child.lineno
                                ),
                                "target": target,
                                "receiver": (
                                    receiver
                                ),
                                "bound_class": (
                                    bound_class
                                ),
                                "binding_type": (
                                    binding_type
                                ),
                                "source": (
                                    source_text(
                                        source,
                                        child.value,
                                    )
                                ),
                            }
                        )

                for child in ast.walk(
                    node
                ):
                    if not isinstance(
                        child,
                        ast.Call,
                    ):
                        continue

                    call_name = dotted_name(
                        child.func
                    )
                    method = (
                        call_name.rsplit(
                            ".",
                            1,
                        )[-1]
                    )

                    if method:
                        call_graph[
                            node.name
                        ].add(method)

                    if method != "decide":
                        continue

                    receiver_expr = (
                        call_name.rsplit(
                            ".",
                            1,
                        )[0]
                        if "."
                        in call_name
                        else ""
                    )
                    receiver = (
                        receiver_expr.rsplit(
                            ".",
                            1,
                        )[-1]
                    )

                    bound_class = (
                        local_bindings.get(
                            receiver,
                            "",
                        )
                    )
                    binding_source = (
                        "ATTRIBUTE_OR_LOCAL"
                    )

                    if (
                        not bound_class
                        and isinstance(
                            child.func,
                            ast.Attribute,
                        )
                        and isinstance(
                            child.func.value,
                            ast.Call,
                        )
                    ):
                        bound_class = (
                            constructor_class(
                                child.func.value,
                                import_aliases,
                            )
                        )
                        binding_source = (
                            "INLINE_CONSTRUCTOR"
                        )

                    candidate = (
                        candidate_by_class_method
                        .get(
                            (
                                bound_class,
                                method,
                            )
                        )
                    )

                    if candidate:
                        result_target = ""

                        for parent in ast.walk(
                            node
                        ):
                            if not isinstance(
                                parent,
                                (
                                    ast.Assign,
                                    ast.AnnAssign,
                                ),
                            ):
                                continue

                            if parent.value is child:
                                targets = (
                                    assignment_targets(
                                        parent
                                    )
                                )
                                result_target = (
                                    targets[0]
                                    if targets
                                    else ""
                                )
                                break

                        call_rows.append(
                            {
                                "candidate_path": (
                                    candidate.path
                                ),
                                "candidate_symbol": (
                                    candidate.symbol
                                ),
                                "candidate_class": (
                                    candidate.class_name
                                ),
                                "caller_path": (
                                    relative
                                ),
                                "caller_class": (
                                    owner_class
                                ),
                                "caller_function": (
                                    node.name
                                ),
                                "caller_symbol": (
                                    caller_symbol
                                ),
                                "call_line": (
                                    child.lineno
                                ),
                                "receiver": (
                                    receiver_expr
                                ),
                                "bound_class": (
                                    bound_class
                                ),
                                "binding_source": (
                                    binding_source
                                ),
                                "result_target": (
                                    result_target
                                ),
                                "call": call_name,
                                "source": (
                                    source_text(
                                        source,
                                        child,
                                    )
                                ),
                            }
                        )
                    else:
                        ambiguous_rows.append(
                            {
                                "caller_path": (
                                    relative
                                ),
                                "caller_symbol": (
                                    caller_symbol
                                ),
                                "call_line": (
                                    child.lineno
                                ),
                                "receiver": (
                                    receiver_expr
                                ),
                                "method": method,
                                "bound_class": (
                                    bound_class
                                ),
                                "call": call_name,
                                "reason": (
                                    "NO_CANDIDATE_CLASS_BINDING"
                                ),
                            }
                        )

                self.generic_visit(node)
                function_stack.pop()

        CallVisitor().visit(tree)

    reverse_graph: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for caller, callees in (
        call_graph.items()
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
    unresolved_rows: list[
        dict[str, object]
    ] = []

    for candidate in candidates:
        rows = [
            row
            for row in call_rows
            if row[
                "candidate_symbol"
            ] == candidate.symbol
        ]

        runtime_count = sum(
            runtime_reachable(
                str(
                    row[
                        "caller_function"
                    ]
                )
            )
            for row in rows
        )

        bound_result_count = sum(
            bool(
                str(
                    row[
                        "result_target"
                    ]
                )
            )
            for row in rows
        )

        if runtime_count > 0:
            classification = (
                "QUALIFIED_RUNTIME_BOUNDARY_CANDIDATE"
            )
        elif rows:
            classification = (
                "QUALIFIED_RESEARCH_BOUNDARY_CANDIDATE"
            )
        else:
            classification = (
                "NO_QUALIFIED_CALL_FOUND"
            )

        summary_rows.append(
            {
                "candidate_path": (
                    candidate.path
                ),
                "candidate_symbol": (
                    candidate.symbol
                ),
                "qualified_call_count": (
                    len(rows)
                ),
                "bound_result_count": (
                    bound_result_count
                ),
                "runtime_reachable_call_count": (
                    runtime_count
                ),
                "classification": (
                    classification
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

        if not rows:
            unresolved_rows.append(
                {
                    "scope": (
                        "CANDIDATE_BINDING"
                    ),
                    "symbol": (
                        candidate.symbol
                    ),
                    "reason": (
                        "NO_QUALIFIED_CALL_FOUND"
                    ),
                }
            )

    write_tsv(
        CANDIDATES_FILE,
        (
            "path",
            "class_name",
            "method",
            "candidate_symbol",
        ),
        candidate_rows,
    )

    write_tsv(
        IMPORTS_FILE,
        (
            "path",
            "line",
            "local_name",
            "imported_name",
            "module",
        ),
        import_rows,
    )

    write_tsv(
        CONSTRUCTORS_FILE,
        (
            "path",
            "caller_symbol",
            "line",
            "target",
            "receiver",
            "bound_class",
            "source",
        ),
        [
            {
                "path": row["path"],
                "caller_symbol": (
                    row["caller_symbol"]
                ),
                "line": row["line"],
                "target": row["target"],
                "receiver": (
                    row["receiver"]
                ),
                "bound_class": (
                    row["bound_class"]
                ),
                "source": row["source"],
            }
            for row in local_rows
            if row["binding_type"]
            == "LOCAL_CONSTRUCTOR"
        ],
    )

    write_tsv(
        ATTRIBUTES_FILE,
        (
            "path",
            "owner_class",
            "line",
            "target",
            "receiver",
            "bound_class",
            "source",
        ),
        attribute_rows,
    )

    write_tsv(
        LOCALS_FILE,
        (
            "path",
            "caller_symbol",
            "line",
            "target",
            "receiver",
            "bound_class",
            "binding_type",
            "source",
        ),
        local_rows,
    )

    write_tsv(
        CALLS_FILE,
        (
            "candidate_path",
            "candidate_symbol",
            "candidate_class",
            "caller_path",
            "caller_class",
            "caller_function",
            "caller_symbol",
            "call_line",
            "receiver",
            "bound_class",
            "binding_source",
            "result_target",
            "call",
            "source",
        ),
        call_rows,
    )

    write_tsv(
        AMBIGUOUS_FILE,
        (
            "caller_path",
            "caller_symbol",
            "call_line",
            "receiver",
            "method",
            "bound_class",
            "call",
            "reason",
        ),
        ambiguous_rows,
    )

    write_tsv(
        SUMMARY_FILE,
        (
            "candidate_path",
            "candidate_symbol",
            "qualified_call_count",
            "bound_result_count",
            "runtime_reachable_call_count",
            "classification",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        summary_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "symbol",
            "reason",
        ),
        unresolved_rows,
    )

    print(
        "=== AUDIT EDGE DECISION BOUNDARY "
        "QUALIFIED BINDING V2 ==="
    )
    print(
        f"candidate_count="
        f"{len(candidates)}"
    )
    print(
        f"import_alias_count="
        f"{len(import_rows)}"
    )
    print(
        f"attribute_binding_count="
        f"{len(attribute_rows)}"
    )
    print(
        f"local_binding_count="
        f"{len(local_rows)}"
    )
    print(
        f"qualified_call_count="
        f"{len(call_rows)}"
    )
    print(
        f"remaining_ambiguous_call_count="
        f"{len(ambiguous_rows)}"
    )
    print(
        f"unresolved_candidate_count="
        f"{len(unresolved_rows)}"
    )

    for row in summary_rows:
        print(
            "QUALIFIED_BOUNDARY "
            f"symbol={row['candidate_symbol']} "
            f"calls={row['qualified_call_count']} "
            f"bound_results={row['bound_result_count']} "
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
        "EDGE_DECISION_BOUNDARY_"
        "QUALIFIED_BINDING_V2_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
