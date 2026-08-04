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
    "/tmp/regime_qualified_call_binding_v2"
)

CANDIDATES_FILE = OUTPUT_DIR / "candidate_classes.tsv"
CONSTRUCTORS_FILE = OUTPUT_DIR / "constructor_bindings.tsv"
ASSIGNMENTS_FILE = OUTPUT_DIR / "assignment_bindings.tsv"
QUALIFIED_CALLS_FILE = OUTPUT_DIR / "qualified_calls.tsv"
AMBIGUOUS_CALLS_FILE = OUTPUT_DIR / "ambiguous_calls.tsv"
SUMMARY_FILE = OUTPUT_DIR / "candidate_summary.tsv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

SOURCE_ROOTS = (
    ROOT / "src/finam_core",
    ROOT / "core",
    ROOT / "strategy",
    ROOT / "risk",
)

RUNTIME_ENTRY_FUNCTIONS = {
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


def target_names(node: ast.Assign | ast.AnnAssign) -> list[str]:
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

    class_index = {
        candidate.class_name: candidate
        for candidate in candidates
        if candidate.class_name
    }

    candidate_by_class_method = {
        (candidate.class_name, candidate.method): candidate
        for candidate in candidates
        if candidate.class_name
    }

    method_to_candidates: dict[str, list[Candidate]] = defaultdict(list)

    for candidate in candidates:
        method_to_candidates[candidate.method].append(candidate)

    candidate_rows = [
        {
            "family": candidate.family,
            "path": candidate.path,
            "class_name": candidate.class_name,
            "method": candidate.method,
            "candidate_symbol": candidate.symbol,
        }
        for candidate in candidates
    ]

    constructor_rows: list[dict[str, object]] = []
    assignment_rows: list[dict[str, object]] = []
    qualified_calls: list[dict[str, object]] = []
    ambiguous_calls: list[dict[str, object]] = []

    call_graph: dict[str, set[str]] = defaultdict(set)

    for path in discover_files():
        relative = str(path.relative_to(ROOT))
        source = path.read_text(encoding="utf-8", errors="replace")

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        class Visitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.class_stack: list[str] = []
                self.function_stack: list[str] = []
                self.bindings: dict[str, str] = {}

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                self.class_stack.append(node.name)
                self.generic_visit(node)
                self.class_stack.pop()

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
                qualified_caller = ".".join(
                    [*self.class_stack, *self.function_stack, node.name]
                )

                previous_bindings = dict(self.bindings)
                self.function_stack.append(node.name)

                for child in ast.walk(node):
                    if isinstance(child, (ast.Assign, ast.AnnAssign)):
                        value = child.value

                        if isinstance(value, ast.Call):
                            constructor = dotted_name(value.func)
                            class_name = constructor.rsplit(".", 1)[-1]

                            if class_name in class_index:
                                for target in target_names(child):
                                    receiver = target.rsplit(".", 1)[-1]
                                    self.bindings[receiver] = class_name

                                    constructor_rows.append(
                                        {
                                            "family": class_index[class_name].family,
                                            "class_name": class_name,
                                            "path": relative,
                                            "caller": qualified_caller,
                                            "line": child.lineno,
                                            "target": target,
                                            "receiver": receiver,
                                            "constructor": constructor,
                                        }
                                    )

                        if isinstance(value, (ast.Name, ast.Attribute)):
                            source_name = dotted_name(value)
                            source_receiver = source_name.rsplit(".", 1)[-1]
                            bound_class = self.bindings.get(source_receiver)

                            if bound_class:
                                for target in target_names(child):
                                    target_receiver = target.rsplit(".", 1)[-1]
                                    self.bindings[target_receiver] = bound_class

                                    assignment_rows.append(
                                        {
                                            "path": relative,
                                            "caller": qualified_caller,
                                            "line": child.lineno,
                                            "source": source_name,
                                            "target": target,
                                            "class_name": bound_class,
                                        }
                                    )

                    if not isinstance(child, ast.Call):
                        continue

                    call = dotted_name(child.func)
                    terminal = call.rsplit(".", 1)[-1]

                    if terminal:
                        call_graph[node.name].add(terminal)

                    candidates_for_method = method_to_candidates.get(
                        terminal,
                        [],
                    )

                    if not candidates_for_method:
                        continue

                    receiver_expr = (
                        call.rsplit(".", 1)[0]
                        if "." in call
                        else ""
                    )
                    receiver = receiver_expr.rsplit(".", 1)[-1]
                    bound_class = self.bindings.get(receiver)

                    resolved = None

                    if bound_class:
                        resolved = candidate_by_class_method.get(
                            (bound_class, terminal)
                        )

                    if resolved:
                        qualified_calls.append(
                            {
                                "family": resolved.family,
                                "candidate_symbol": resolved.symbol,
                                "candidate_class": resolved.class_name,
                                "candidate_method": resolved.method,
                                "path": relative,
                                "caller": qualified_caller,
                                "caller_function": node.name,
                                "line": child.lineno,
                                "receiver": receiver_expr,
                                "bound_class": bound_class,
                                "call": call,
                                "source": source_text(source, child),
                            }
                        )
                    else:
                        ambiguous_calls.append(
                            {
                                "path": relative,
                                "caller": qualified_caller,
                                "caller_function": node.name,
                                "line": child.lineno,
                                "receiver": receiver_expr,
                                "method": terminal,
                                "candidate_count": len(candidates_for_method),
                                "candidate_symbols": ",".join(
                                    sorted(
                                        candidate.symbol
                                        for candidate in candidates_for_method
                                    )
                                ),
                                "call": call,
                                "source": source_text(source, child),
                            }
                        )

                self.generic_visit(node)
                self.function_stack.pop()
                self.bindings = previous_bindings

        Visitor().visit(tree)

    reverse_graph: dict[str, set[str]] = defaultdict(set)

    for caller, callees in call_graph.items():
        for callee in callees:
            reverse_graph[callee].add(caller)

    def runtime_reachable(
        function_name: str,
    ) -> tuple[bool, str]:
        queue: list[tuple[str, list[str]]] = [
            (function_name, [function_name])
        ]
        visited: set[str] = set()

        while queue:
            current, chain = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            if current in RUNTIME_ENTRY_FUNCTIONS:
                return True, "->".join(reversed(chain))

            for parent in sorted(reverse_graph.get(current, set())):
                queue.append((parent, [*chain, parent]))

        return False, ""

    calls_by_symbol: dict[str, list[dict[str, object]]] = defaultdict(list)

    for row in qualified_calls:
        calls_by_symbol[str(row["candidate_symbol"])].append(row)

    summary_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []

    for candidate in candidates:
        rows = calls_by_symbol.get(candidate.symbol, [])
        runtime_count = 0
        chains: set[str] = set()

        for row in rows:
            reachable, chain = runtime_reachable(
                str(row["caller_function"])
            )

            if reachable:
                runtime_count += 1
                chains.add(chain)

        if candidate.symbol in INTERNAL_HELPERS:
            classification = "INTERNAL_HELPER"
        elif runtime_count > 0:
            classification = "QUALIFIED_RUNTIME_REACHABLE"
        elif rows:
            classification = "QUALIFIED_CALL_NOT_RUNTIME_PROVEN"
        elif not candidate.class_name:
            classification = "MODULE_FUNCTION_REQUIRES_SEPARATE_PROOF"
        else:
            classification = "NO_QUALIFIED_CALL_FOUND"

        summary_rows.append(
            {
                "family": candidate.family,
                "candidate_symbol": candidate.symbol,
                "qualified_call_count": len(rows),
                "runtime_reachable_call_count": runtime_count,
                "runtime_chains": ",".join(sorted(chains)),
                "classification": classification,
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

        if classification == "NO_QUALIFIED_CALL_FOUND":
            unresolved_rows.append(
                {
                    "family": candidate.family,
                    "candidate_symbol": candidate.symbol,
                    "reason": "NO_CLASS_QUALIFIED_CALL_FOUND",
                }
            )

    write_tsv(
        CANDIDATES_FILE,
        (
            "family",
            "path",
            "class_name",
            "method",
            "candidate_symbol",
        ),
        candidate_rows,
    )

    write_tsv(
        CONSTRUCTORS_FILE,
        (
            "family",
            "class_name",
            "path",
            "caller",
            "line",
            "target",
            "receiver",
            "constructor",
        ),
        constructor_rows,
    )

    write_tsv(
        ASSIGNMENTS_FILE,
        (
            "path",
            "caller",
            "line",
            "source",
            "target",
            "class_name",
        ),
        assignment_rows,
    )

    write_tsv(
        QUALIFIED_CALLS_FILE,
        (
            "family",
            "candidate_symbol",
            "candidate_class",
            "candidate_method",
            "path",
            "caller",
            "caller_function",
            "line",
            "receiver",
            "bound_class",
            "call",
            "source",
        ),
        qualified_calls,
    )

    write_tsv(
        AMBIGUOUS_CALLS_FILE,
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
        ambiguous_calls,
    )

    write_tsv(
        SUMMARY_FILE,
        (
            "family",
            "candidate_symbol",
            "qualified_call_count",
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

    print("=== AUDIT REGIME QUALIFIED CALL BINDING V2 ===")
    print(f"candidate_count={len(candidates)}")
    print(f"constructor_binding_count={len(constructor_rows)}")
    print(f"assignment_binding_count={len(assignment_rows)}")
    print(f"qualified_call_count={len(qualified_calls)}")
    print(f"ambiguous_call_count={len(ambiguous_calls)}")
    print(
        "qualified_runtime_reachable_candidate_count="
        f"{sum(row['classification'] == 'QUALIFIED_RUNTIME_REACHABLE' for row in summary_rows)}"
    )
    print(f"unresolved_count={len(unresolved_rows)}")

    for row in summary_rows:
        print(
            f"QUALIFIED_REACHABILITY family={row['family']} "
            f"symbol={row['candidate_symbol']} "
            f"qualified_calls={row['qualified_call_count']} "
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
    print("VERDICT=REGIME_QUALIFIED_CALL_BINDING_V2_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
