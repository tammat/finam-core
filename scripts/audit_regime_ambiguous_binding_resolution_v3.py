#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from collections import defaultdict
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

CLASSIFIER_FILE = pathlib.Path(
    "/tmp/regime_semantic_classification_v1/classifier_candidates.tsv"
)
FAMILY_FILE = pathlib.Path(
    "/tmp/regime_semantic_classification_v1/family_specific_candidates.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/regime_ambiguous_binding_resolution_v3"
)

IMPORTS_FILE = OUTPUT_DIR / "import_aliases.tsv"
BINDINGS_FILE = OUTPUT_DIR / "persistent_bindings.tsv"
RESOLVED_FILE = OUTPUT_DIR / "resolved_calls.tsv"
AMBIGUOUS_FILE = OUTPUT_DIR / "remaining_ambiguous_calls.tsv"
SUMMARY_FILE = OUTPUT_DIR / "candidate_summary.tsv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

SOURCE_ROOTS = (
    ROOT / "src/finam_core",
    ROOT / "core",
    ROOT / "strategy",
    ROOT / "risk",
)

RUNTIME_ENTRYPOINTS = {
    "_on_quote_impl",
    "_record_live_quote_to_storage",
    "_process_br_closed_bar_for_paper_signal",
    "_process_ng_m1_closed_bar_for_paper_signal",
    "_process_equity_closed_bar_for_paper_signal",
}

INTERNAL_HELPERS = {
    "RegimeLabeler._trend_label",
    "RegimeLabeler._vol_label",
}


@dataclass(frozen=True, slots=True)
class Candidate:
    family: str
    path: str
    class_name: str
    method: str
    symbol: str


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"source_missing:{path}")

    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


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

    return ""


def source_text(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""

    try:
        return ast.get_source_segment(source, node) or ""
    except (IndexError, ValueError):
        return ""


def assignment_targets(
    node: ast.Assign | ast.AnnAssign,
) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return list(node.targets)

    return [node.target]


def discover_files() -> list[pathlib.Path]:
    files: set[pathlib.Path] = set()

    for root in SOURCE_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*.py"):
            if "__pycache__" not in path.parts:
                files.add(path.resolve())

    return sorted(files)


def load_candidates() -> list[Candidate]:
    rows = read_tsv(CLASSIFIER_FILE) + read_tsv(FAMILY_FILE)

    return [
        Candidate(
            family=row["family"],
            path=row["path"],
            class_name=row["class_name"],
            method=row["function"],
            symbol=row["qualified_name"],
        )
        for row in rows
    ]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    candidates = load_candidates()

    candidate_by_class_method = {
        (candidate.class_name, candidate.method): candidate
        for candidate in candidates
        if candidate.class_name
    }

    method_index: dict[str, list[Candidate]] = defaultdict(list)

    for candidate in candidates:
        method_index[candidate.method].append(candidate)

    import_rows: list[dict[str, object]] = []
    binding_rows: list[dict[str, object]] = []
    resolved_rows: list[dict[str, object]] = []
    ambiguous_rows: list[dict[str, object]] = []

    call_graph: dict[str, set[str]] = defaultdict(set)

    for path in discover_files():
        relative = str(path.relative_to(ROOT))
        source = path.read_text(encoding="utf-8", errors="replace")

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        import_aliases: dict[str, str] = {}

        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    local_name = alias.asname or alias.name
                    import_aliases[local_name] = alias.name

                    import_rows.append(
                        {
                            "path": relative,
                            "line": node.lineno,
                            "local_name": local_name,
                            "imported_name": alias.name,
                            "module": node.module or "",
                        }
                    )

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    local_name = alias.asname or alias.name
                    imported_name = alias.name.rsplit(".", 1)[-1]
                    import_aliases[local_name] = imported_name

                    import_rows.append(
                        {
                            "path": relative,
                            "line": node.lineno,
                            "local_name": local_name,
                            "imported_name": imported_name,
                            "module": alias.name,
                        }
                    )

        class_bindings: dict[str, dict[str, str]] = defaultdict(dict)

        # Первый проход: устойчивые bindings self.<attr> = CandidateClass(...).
        class_stack: list[str] = []

        class BindingVisitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                class_stack.append(node.name)
                self.generic_visit(node)
                class_stack.pop()

            def visit_Assign(self, node: ast.Assign) -> None:
                self._assignment(node)
                self.generic_visit(node)

            def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
                self._assignment(node)
                self.generic_visit(node)

            def _assignment(
                self,
                node: ast.Assign | ast.AnnAssign,
            ) -> None:
                if not class_stack or node.value is None:
                    return

                class_name = ""

                if isinstance(node.value, ast.Call):
                    constructor = dotted_name(node.value.func)
                    terminal = constructor.rsplit(".", 1)[-1]
                    class_name = import_aliases.get(terminal, terminal)

                elif isinstance(node.value, (ast.Name, ast.Attribute)):
                    source_name = dotted_name(node.value)
                    source_receiver = source_name.rsplit(".", 1)[-1]
                    class_name = class_bindings[
                        class_stack[-1]
                    ].get(source_receiver, "")

                if not class_name:
                    return

                if not any(
                    candidate.class_name == class_name
                    for candidate in candidates
                ):
                    return

                for target in assignment_targets(node):
                    target_name = dotted_name(target)

                    if not target_name:
                        continue

                    receiver = target_name.rsplit(".", 1)[-1]
                    class_bindings[class_stack[-1]][receiver] = class_name

                    binding_rows.append(
                        {
                            "path": relative,
                            "owner_class": class_stack[-1],
                            "line": node.lineno,
                            "target": target_name,
                            "receiver": receiver,
                            "bound_class": class_name,
                            "source": source_text(source, node.value),
                        }
                    )

        BindingVisitor().visit(tree)

        class_stack = []
        function_stack: list[str] = []

        class CallVisitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                class_stack.append(node.name)
                self.generic_visit(node)
                class_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._function(node)

            def visit_AsyncFunctionDef(
                self,
                node: ast.AsyncFunctionDef,
            ) -> None:
                self._function(node)

            def _function(
                self,
                node: ast.FunctionDef | ast.AsyncFunctionDef,
            ) -> None:
                qualified_caller = ".".join(
                    [*class_stack, *function_stack, node.name]
                )

                local_bindings = dict(
                    class_bindings.get(
                        class_stack[-1] if class_stack else "",
                        {},
                    )
                )

                function_stack.append(node.name)

                # Локальные bindings.
                for child in ast.walk(node):
                    if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                        continue

                    if child.value is None:
                        continue

                    bound_class = ""

                    if isinstance(child.value, ast.Call):
                        constructor = dotted_name(child.value.func)
                        terminal = constructor.rsplit(".", 1)[-1]
                        bound_class = import_aliases.get(terminal, terminal)

                    elif isinstance(child.value, (ast.Name, ast.Attribute)):
                        source_name = dotted_name(child.value)
                        source_receiver = source_name.rsplit(".", 1)[-1]
                        bound_class = local_bindings.get(source_receiver, "")

                    if not bound_class:
                        continue

                    if not any(
                        candidate.class_name == bound_class
                        for candidate in candidates
                    ):
                        continue

                    for target in assignment_targets(child):
                        target_name = dotted_name(target)

                        if target_name:
                            local_bindings[
                                target_name.rsplit(".", 1)[-1]
                            ] = bound_class

                for child in ast.walk(node):
                    if not isinstance(child, ast.Call):
                        continue

                    call = dotted_name(child.func)
                    method = call.rsplit(".", 1)[-1]

                    if method:
                        call_graph[node.name].add(method)

                    method_candidates = method_index.get(method, [])

                    if not method_candidates:
                        continue

                    receiver_expr = (
                        call.rsplit(".", 1)[0]
                        if "." in call
                        else ""
                    )
                    receiver = receiver_expr.rsplit(".", 1)[-1]

                    bound_class = local_bindings.get(receiver, "")
                    binding_source = "ATTRIBUTE_OR_LOCAL"

                    # Inline constructor: RegimeEngine(...).evaluate(...)
                    if not bound_class and isinstance(
                        child.func,
                        ast.Attribute,
                    ):
                        value = child.func.value

                        if isinstance(value, ast.Call):
                            constructor = dotted_name(value.func)
                            terminal = constructor.rsplit(".", 1)[-1]
                            bound_class = import_aliases.get(
                                terminal,
                                terminal,
                            )
                            binding_source = "INLINE_CONSTRUCTOR"

                    resolved = candidate_by_class_method.get(
                        (bound_class, method)
                    )

                    if resolved:
                        resolved_rows.append(
                            {
                                "family": resolved.family,
                                "candidate_symbol": resolved.symbol,
                                "path": relative,
                                "caller": qualified_caller,
                                "caller_function": node.name,
                                "line": child.lineno,
                                "receiver": receiver_expr,
                                "bound_class": bound_class,
                                "binding_source": binding_source,
                                "call": call,
                                "source": source_text(source, child),
                            }
                        )
                    else:
                        ambiguous_rows.append(
                            {
                                "path": relative,
                                "caller": qualified_caller,
                                "caller_function": node.name,
                                "line": child.lineno,
                                "receiver": receiver_expr,
                                "method": method,
                                "candidate_count": len(method_candidates),
                                "candidate_symbols": ",".join(
                                    sorted(
                                        candidate.symbol
                                        for candidate in method_candidates
                                    )
                                ),
                                "call": call,
                                "source": source_text(source, child),
                            }
                        )

                self.generic_visit(node)
                function_stack.pop()

        CallVisitor().visit(tree)

    reverse_graph: dict[str, set[str]] = defaultdict(set)

    for caller, callees in call_graph.items():
        for callee in callees:
            reverse_graph[callee].add(caller)

    def runtime_reachable(function_name: str) -> tuple[bool, str]:
        queue: list[tuple[str, list[str]]] = [
            (function_name, [function_name])
        ]
        visited: set[str] = set()

        while queue:
            current, chain = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            if current in RUNTIME_ENTRYPOINTS:
                return True, "->".join(reversed(chain))

            for parent in sorted(reverse_graph.get(current, set())):
                queue.append((parent, [*chain, parent]))

        return False, ""

    resolved_by_symbol: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in resolved_rows:
        resolved_by_symbol[str(row["candidate_symbol"])].append(row)

    summary_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []

    for candidate in candidates:
        calls = resolved_by_symbol.get(candidate.symbol, [])
        runtime_count = 0
        chains: set[str] = set()

        for row in calls:
            reachable, chain = runtime_reachable(
                str(row["caller_function"])
            )

            if reachable:
                runtime_count += 1
                chains.add(chain)

        if candidate.symbol in INTERNAL_HELPERS:
            classification = "INTERNAL_HELPER"
        elif runtime_count > 0:
            classification = "RESOLVED_RUNTIME_REACHABLE"
        elif calls:
            classification = "RESOLVED_NOT_RUNTIME_PROVEN"
        elif not candidate.class_name:
            classification = "MODULE_FUNCTION_DEFERRED"
        else:
            classification = "NO_RESOLVED_BINDING"

        summary_rows.append(
            {
                "family": candidate.family,
                "candidate_symbol": candidate.symbol,
                "resolved_call_count": len(calls),
                "runtime_reachable_call_count": runtime_count,
                "runtime_chains": ",".join(sorted(chains)),
                "classification": classification,
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

        if classification == "NO_RESOLVED_BINDING":
            unresolved_rows.append(
                {
                    "family": candidate.family,
                    "candidate_symbol": candidate.symbol,
                    "reason": "NO_RESOLVED_RUNTIME_BINDING",
                }
            )

    write_tsv(
        IMPORTS_FILE,
        ("path", "line", "local_name", "imported_name", "module"),
        import_rows,
    )

    write_tsv(
        BINDINGS_FILE,
        (
            "path",
            "owner_class",
            "line",
            "target",
            "receiver",
            "bound_class",
            "source",
        ),
        binding_rows,
    )

    write_tsv(
        RESOLVED_FILE,
        (
            "family",
            "candidate_symbol",
            "path",
            "caller",
            "caller_function",
            "line",
            "receiver",
            "bound_class",
            "binding_source",
            "call",
            "source",
        ),
        resolved_rows,
    )

    write_tsv(
        AMBIGUOUS_FILE,
        (
            "path",
            "caller",
            "caller_function",
            "line",
            "receiver",
            "method",
            "candidate_count",
            "candidate_symbols",
            "call",
            "source",
        ),
        ambiguous_rows,
    )

    write_tsv(
        SUMMARY_FILE,
        (
            "family",
            "candidate_symbol",
            "resolved_call_count",
            "runtime_reachable_call_count",
            "runtime_chains",
            "classification",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        summary_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        ("family", "candidate_symbol", "reason"),
        unresolved_rows,
    )

    print("=== AUDIT REGIME AMBIGUOUS BINDING RESOLUTION V3 ===")
    print(f"candidate_count={len(candidates)}")
    print(f"import_alias_count={len(import_rows)}")
    print(f"persistent_binding_count={len(binding_rows)}")
    print(f"resolved_call_count={len(resolved_rows)}")
    print(f"remaining_ambiguous_call_count={len(ambiguous_rows)}")
    print(
        "resolved_runtime_reachable_candidate_count="
        f"{sum(row['classification'] == 'RESOLVED_RUNTIME_REACHABLE' for row in summary_rows)}"
    )
    print(f"unresolved_count={len(unresolved_rows)}")

    for row in summary_rows:
        print(
            f"RESOLUTION family={row['family']} "
            f"symbol={row['candidate_symbol']} "
            f"resolved_calls={row['resolved_call_count']} "
            f"runtime_calls={row['runtime_reachable_call_count']} "
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
    print("VERDICT=REGIME_AMBIGUOUS_BINDING_RESOLUTION_V3_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
