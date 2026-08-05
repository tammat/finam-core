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
    "/tmp/edge_candidate_dependency_injection_v3"
)

CANDIDATES_FILE = OUT / "candidate_identities.tsv"
IMPORTS_FILE = OUT / "import_sites.tsv"
ANNOTATIONS_FILE = OUT / "annotation_bindings.tsv"
PARAMETERS_FILE = OUT / "parameter_bindings.tsv"
FACTORIES_FILE = OUT / "factory_returns.tsv"
MODULE_INSTANCES_FILE = OUT / "module_instances.tsv"
ASSIGNMENTS_FILE = OUT / "dependency_assignments.tsv"
CALLS_FILE = OUT / "resolved_decide_calls.tsv"
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


@dataclass(frozen=True, slots=True)
class Candidate:
    path: str
    class_name: str
    method: str
    symbol: str


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"source_file_missing:{path}")

    with path.open("r", encoding="utf-8", newline="") as stream:
        return [
            {key: str(value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(stream, delimiter="\t")
        ]


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
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


def dotted_name(node: ast.AST | None) -> str:
    if node is None:
        return ""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    if isinstance(node, ast.Subscript):
        return dotted_name(node.value)

    if isinstance(node, ast.Constant):
        return str(node.value)

    return ""


def source_text(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""

    try:
        return ast.get_source_segment(source, node) or ""
    except (IndexError, ValueError):
        return ""


def annotation_terminal(node: ast.AST | None) -> str:
    value = dotted_name(node)
    return value.rsplit(".", 1)[-1]


def assignment_targets(
    node: ast.Assign | ast.AnnAssign,
) -> list[str]:
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]

    result: list[str] = []

    for target in targets:
        name = dotted_name(target)

        if name:
            result.append(name)

    return result


def discover_files() -> list[pathlib.Path]:
    result: set[pathlib.Path] = set()

    for root in SOURCE_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*.py"):
            if "__pycache__" not in path.parts:
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    candidates = load_candidates()
    candidate_classes = {candidate.class_name for candidate in candidates}
    candidate_by_class = {
        candidate.class_name: candidate
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
    annotation_rows: list[dict[str, object]] = []
    parameter_rows: list[dict[str, object]] = []
    factory_rows: list[dict[str, object]] = []
    module_instance_rows: list[dict[str, object]] = []
    assignment_rows: list[dict[str, object]] = []
    call_rows: list[dict[str, object]] = []

    for path in discover_files():
        relative = str(path.relative_to(ROOT))
        source = path.read_text(encoding="utf-8", errors="replace")

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        aliases: dict[str, str] = {}

        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    local = alias.asname or alias.name
                    imported = alias.name.rsplit(".", 1)[-1]
                    aliases[local] = imported

                    if imported in candidate_classes:
                        import_rows.append(
                            {
                                "path": relative,
                                "line": node.lineno,
                                "local_name": local,
                                "candidate_class": imported,
                                "module": node.module or "",
                            }
                        )

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name
                    imported = alias.name.rsplit(".", 1)[-1]
                    aliases[local] = imported

                    if imported in candidate_classes:
                        import_rows.append(
                            {
                                "path": relative,
                                "line": node.lineno,
                                "local_name": local,
                                "candidate_class": imported,
                                "module": alias.name,
                            }
                        )

        class_stack: list[str] = []
        function_stack: list[str] = []

        class Visitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                class_stack.append(node.name)
                self.generic_visit(node)
                class_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._visit_function(node)

            def visit_AsyncFunctionDef(
                self,
                node: ast.AsyncFunctionDef,
            ) -> None:
                self._visit_function(node)

            def _visit_function(
                self,
                node: ast.FunctionDef | ast.AsyncFunctionDef,
            ) -> None:
                function_stack.append(node.name)

                symbol = ".".join(
                    [*class_stack, *function_stack]
                )

                bindings: dict[str, str] = {}

                all_args = [
                    *node.args.posonlyargs,
                    *node.args.args,
                    *node.args.kwonlyargs,
                ]

                for arg in all_args:
                    bound_class = annotation_terminal(arg.annotation)
                    bound_class = aliases.get(bound_class, bound_class)

                    if bound_class not in candidate_classes:
                        continue

                    bindings[arg.arg] = bound_class

                    parameter_rows.append(
                        {
                            "path": relative,
                            "function_symbol": symbol,
                            "line": arg.lineno,
                            "parameter": arg.arg,
                            "candidate_class": bound_class,
                            "annotation": source_text(source, arg.annotation),
                        }
                    )

                for child in ast.walk(node):
                    if isinstance(child, ast.AnnAssign):
                        bound_class = annotation_terminal(child.annotation)
                        bound_class = aliases.get(bound_class, bound_class)

                        if bound_class in candidate_classes:
                            for target in assignment_targets(child):
                                receiver = target.rsplit(".", 1)[-1]
                                bindings[receiver] = bound_class

                                annotation_rows.append(
                                    {
                                        "path": relative,
                                        "function_symbol": symbol,
                                        "line": child.lineno,
                                        "target": target,
                                        "candidate_class": bound_class,
                                        "annotation": source_text(
                                            source,
                                            child.annotation,
                                        ),
                                    }
                                )

                    if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                        continue

                    if child.value is None:
                        continue

                    bound_class = ""

                    if isinstance(child.value, ast.Call):
                        constructor = dotted_name(child.value.func)
                        terminal = constructor.rsplit(".", 1)[-1]
                        bound_class = aliases.get(terminal, terminal)

                    elif isinstance(child.value, (ast.Name, ast.Attribute)):
                        source_name = dotted_name(child.value)
                        source_receiver = source_name.rsplit(".", 1)[-1]
                        bound_class = bindings.get(source_receiver, "")

                    if bound_class not in candidate_classes:
                        continue

                    for target in assignment_targets(child):
                        receiver = target.rsplit(".", 1)[-1]
                        bindings[receiver] = bound_class

                        assignment_rows.append(
                            {
                                "path": relative,
                                "function_symbol": symbol,
                                "line": child.lineno,
                                "target": target,
                                "receiver": receiver,
                                "candidate_class": bound_class,
                                "source": source_text(source, child.value),
                            }
                        )

                for child in ast.walk(node):
                    if not isinstance(child, ast.Return):
                        continue

                    returned_class = ""

                    if isinstance(child.value, ast.Call):
                        constructor = dotted_name(child.value.func)
                        terminal = constructor.rsplit(".", 1)[-1]
                        returned_class = aliases.get(terminal, terminal)

                    elif isinstance(child.value, (ast.Name, ast.Attribute)):
                        returned_name = dotted_name(child.value)
                        returned_receiver = returned_name.rsplit(".", 1)[-1]
                        returned_class = bindings.get(returned_receiver, "")

                    if returned_class in candidate_classes:
                        factory_rows.append(
                            {
                                "path": relative,
                                "factory_symbol": symbol,
                                "line": child.lineno,
                                "candidate_class": returned_class,
                                "return_source": source_text(source, child.value),
                            }
                        )

                for child in ast.walk(node):
                    if not isinstance(child, ast.Call):
                        continue

                    call_name = dotted_name(child.func)

                    if not call_name.endswith(".decide"):
                        continue

                    receiver_expr = call_name.rsplit(".", 1)[0]
                    receiver = receiver_expr.rsplit(".", 1)[-1]
                    bound_class = bindings.get(receiver, "")

                    if bound_class not in candidate_classes:
                        continue

                    candidate = candidate_by_class[bound_class]

                    call_rows.append(
                        {
                            "candidate_path": candidate.path,
                            "candidate_symbol": candidate.symbol,
                            "caller_path": relative,
                            "caller_symbol": symbol,
                            "call_line": child.lineno,
                            "receiver": receiver_expr,
                            "candidate_class": bound_class,
                            "binding_source": "PARAMETER_OR_ANNOTATION_OR_ALIAS",
                            "call": call_name,
                            "source": source_text(source, child),
                        }
                    )

                self.generic_visit(node)
                function_stack.pop()

        Visitor().visit(tree)

        # Module-level candidate instances.
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue

            if node.value is None:
                continue

            bound_class = ""

            if isinstance(node.value, ast.Call):
                constructor = dotted_name(node.value.func)
                terminal = constructor.rsplit(".", 1)[-1]
                bound_class = aliases.get(terminal, terminal)

            elif isinstance(node, ast.AnnAssign):
                bound_class = annotation_terminal(node.annotation)
                bound_class = aliases.get(bound_class, bound_class)

            if bound_class not in candidate_classes:
                continue

            for target in assignment_targets(node):
                module_instance_rows.append(
                    {
                        "path": relative,
                        "line": node.lineno,
                        "target": target,
                        "candidate_class": bound_class,
                        "source": source_text(source, node.value),
                    }
                )

    summary_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []

    for candidate in candidates:
        imports = [
            row
            for row in import_rows
            if row["candidate_class"] == candidate.class_name
        ]
        annotations = [
            row
            for row in annotation_rows
            if row["candidate_class"] == candidate.class_name
        ]
        parameters = [
            row
            for row in parameter_rows
            if row["candidate_class"] == candidate.class_name
        ]
        factories = [
            row
            for row in factory_rows
            if row["candidate_class"] == candidate.class_name
        ]
        module_instances = [
            row
            for row in module_instance_rows
            if row["candidate_class"] == candidate.class_name
        ]
        assignments = [
            row
            for row in assignment_rows
            if row["candidate_class"] == candidate.class_name
        ]
        calls = [
            row
            for row in call_rows
            if row["candidate_symbol"] == candidate.symbol
        ]

        if calls:
            classification = "DEPENDENCY_INJECTED_CALL_RESOLVED"
        elif parameters or annotations:
            classification = "DEPENDENCY_INJECTED_NO_CALL_PROOF"
        elif factories:
            classification = "FACTORY_PROVIDED_NO_CALL_PROOF"
        elif module_instances or assignments:
            classification = "INSTANCE_EXISTS_NO_CALL_PROOF"
        elif imports:
            classification = "IMPORTED_NOT_CONSTRUCTED"
        else:
            classification = "NO_CONSTRUCTION_OR_INJECTION_FOUND"

        summary_rows.append(
            {
                "candidate_path": candidate.path,
                "candidate_symbol": candidate.symbol,
                "import_count": len(imports),
                "parameter_binding_count": len(parameters),
                "annotation_binding_count": len(annotations),
                "factory_return_count": len(factories),
                "module_instance_count": len(module_instances),
                "dependency_assignment_count": len(assignments),
                "resolved_call_count": len(calls),
                "classification": classification,
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

        if not calls:
            unresolved_rows.append(
                {
                    "scope": "CANDIDATE_BINDING",
                    "symbol": candidate.symbol,
                    "reason": classification,
                }
            )

    write_tsv(
        CANDIDATES_FILE,
        ("path", "class_name", "method", "candidate_symbol"),
        candidate_rows,
    )

    write_tsv(
        IMPORTS_FILE,
        ("path", "line", "local_name", "candidate_class", "module"),
        import_rows,
    )

    write_tsv(
        ANNOTATIONS_FILE,
        (
            "path",
            "function_symbol",
            "line",
            "target",
            "candidate_class",
            "annotation",
        ),
        annotation_rows,
    )

    write_tsv(
        PARAMETERS_FILE,
        (
            "path",
            "function_symbol",
            "line",
            "parameter",
            "candidate_class",
            "annotation",
        ),
        parameter_rows,
    )

    write_tsv(
        FACTORIES_FILE,
        (
            "path",
            "factory_symbol",
            "line",
            "candidate_class",
            "return_source",
        ),
        factory_rows,
    )

    write_tsv(
        MODULE_INSTANCES_FILE,
        ("path", "line", "target", "candidate_class", "source"),
        module_instance_rows,
    )

    write_tsv(
        ASSIGNMENTS_FILE,
        (
            "path",
            "function_symbol",
            "line",
            "target",
            "receiver",
            "candidate_class",
            "source",
        ),
        assignment_rows,
    )

    write_tsv(
        CALLS_FILE,
        (
            "candidate_path",
            "candidate_symbol",
            "caller_path",
            "caller_symbol",
            "call_line",
            "receiver",
            "candidate_class",
            "binding_source",
            "call",
            "source",
        ),
        call_rows,
    )

    write_tsv(
        SUMMARY_FILE,
        (
            "candidate_path",
            "candidate_symbol",
            "import_count",
            "parameter_binding_count",
            "annotation_binding_count",
            "factory_return_count",
            "module_instance_count",
            "dependency_assignment_count",
            "resolved_call_count",
            "classification",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        summary_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        ("scope", "symbol", "reason"),
        unresolved_rows,
    )

    print("=== AUDIT EDGE CANDIDATE DEPENDENCY INJECTION V3 ===")
    print(f"candidate_count={len(candidates)}")
    print(f"candidate_import_count={len(import_rows)}")
    print(f"parameter_binding_count={len(parameter_rows)}")
    print(f"annotation_binding_count={len(annotation_rows)}")
    print(f"factory_return_count={len(factory_rows)}")
    print(f"module_instance_count={len(module_instance_rows)}")
    print(f"dependency_assignment_count={len(assignment_rows)}")
    print(f"resolved_call_count={len(call_rows)}")
    print(f"unresolved_candidate_count={len(unresolved_rows)}")

    for row in summary_rows:
        print(
            "DEPENDENCY_BINDING "
            f"symbol={row['candidate_symbol']} "
            f"imports={row['import_count']} "
            f"parameters={row['parameter_binding_count']} "
            f"annotations={row['annotation_binding_count']} "
            f"factories={row['factory_return_count']} "
            f"instances={row['module_instance_count']} "
            f"assignments={row['dependency_assignment_count']} "
            f"calls={row['resolved_call_count']} "
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
    print("VERDICT=EDGE_CANDIDATE_DEPENDENCY_INJECTION_V3_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
