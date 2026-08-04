#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

SOURCE_ROOTS = (
    ROOT / "src/finam_core",
    ROOT / "core",
    ROOT / "strategy",
)

PRIMARY_FILE = pathlib.Path(
    "/tmp/strategy_owner_family_classification_v1/"
    "primary_candidates.tsv"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/strategy_runtime_binding_discovery_v2"
)

CONSTRUCTORS_FILE = OUTPUT_DIR / "constructor_sites.tsv"
BINDINGS_FILE = OUTPUT_DIR / "binding_sites.tsv"
INTERFACE_CALLS_FILE = OUTPUT_DIR / "interface_calls.tsv"
CLASS_CALLS_FILE = OUTPUT_DIR / "class_method_calls.tsv"
SUMMARY_FILE = OUTPUT_DIR / "candidate_binding_summary.tsv"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

INTERFACE_METHODS = {
    "on_signal_bar",
    "on_bars",
    "on_bar",
    "on_quote",
    "generate",
}

REGISTRY_METHOD_MARKERS = {
    "register",
    "add",
    "append",
    "extend",
    "setdefault",
}


@dataclass(frozen=True, slots=True)
class Candidate:
    family: str
    path: str
    class_name: str
    method: str
    symbol: str


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


def read_candidates() -> list[Candidate]:
    if not PRIMARY_FILE.is_file():
        raise RuntimeError(f"primary_candidates_missing:{PRIMARY_FILE}")

    with PRIMARY_FILE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        return [
            Candidate(
                family=row["family"],
                path=row["path"],
                class_name=row["class_name"],
                method=row["function"],
                symbol=row["qualified_name"],
            )
            for row in csv.DictReader(stream, delimiter="\t")
        ]


def discover_python_files() -> list[pathlib.Path]:
    result: set[pathlib.Path] = set()

    for root in SOURCE_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*.py"):
            if "__pycache__" not in path.parts:
                result.add(path.resolve())

    return sorted(result)


def target_text(source: str, node: ast.Assign | ast.AnnAssign) -> str:
    if isinstance(node, ast.Assign):
        return ",".join(
            source_text(source, target)
            for target in node.targets
        )

    return source_text(source, node.target)


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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    candidates = read_candidates()
    class_index = {
        candidate.class_name: candidate
        for candidate in candidates
    }

    method_index = {
        (candidate.class_name, candidate.method): candidate
        for candidate in candidates
    }

    constructor_rows: list[dict[str, object]] = []
    binding_rows: list[dict[str, object]] = []
    interface_rows: list[dict[str, object]] = []
    class_call_rows: list[dict[str, object]] = []

    for path in discover_python_files():
        relative = str(path.relative_to(ROOT))
        source = path.read_text(encoding="utf-8", errors="replace")

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        scope: dict[ast.AST, str] = {}

        class ScopeVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.stack: list[str] = []

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                self.stack.append(node.name)
                self.generic_visit(node)
                self.stack.pop()

            def _function(
                self,
                node: ast.FunctionDef | ast.AsyncFunctionDef,
            ) -> None:
                self.stack.append(node.name)
                scope[node] = ".".join(self.stack)
                self.generic_visit(node)
                self.stack.pop()

            visit_FunctionDef = _function
            visit_AsyncFunctionDef = _function

        ScopeVisitor().visit(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call = dotted_name(node.func)
                terminal = call.rsplit(".", 1)[-1]

                if terminal in class_index:
                    candidate = class_index[terminal]

                    constructor_rows.append(
                        {
                            "family": candidate.family,
                            "class_name": terminal,
                            "path": relative,
                            "line": node.lineno,
                            "call": call,
                            "source": source_text(source, node),
                        }
                    )

                if terminal in INTERFACE_METHODS:
                    interface_rows.append(
                        {
                            "path": relative,
                            "line": node.lineno,
                            "receiver": call.rsplit(".", 1)[0],
                            "method": terminal,
                            "call": call,
                            "source": source_text(source, node),
                        }
                    )

                for candidate in candidates:
                    if terminal != candidate.method:
                        continue

                    class_call_rows.append(
                        {
                            "family": candidate.family,
                            "candidate_symbol": candidate.symbol,
                            "path": relative,
                            "line": node.lineno,
                            "call": call,
                            "source": source_text(source, node),
                        }
                    )

                if (
                    terminal in REGISTRY_METHOD_MARKERS
                    and node.args
                ):
                    for arg in node.args:
                        if not isinstance(arg, ast.Call):
                            continue

                        constructor = dotted_name(arg.func)
                        class_name = constructor.rsplit(".", 1)[-1]

                        if class_name not in class_index:
                            continue

                        candidate = class_index[class_name]

                        binding_rows.append(
                            {
                                "family": candidate.family,
                                "class_name": class_name,
                                "binding_type": "REGISTRY_CALL",
                                "path": relative,
                                "line": node.lineno,
                                "target": call,
                                "source": source_text(source, node),
                            }
                        )

            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value

                if value is None:
                    continue

                target = target_text(source, node)

                nested_calls = [
                    child
                    for child in ast.walk(value)
                    if isinstance(child, ast.Call)
                ]

                for call_node in nested_calls:
                    constructor = dotted_name(call_node.func)
                    class_name = constructor.rsplit(".", 1)[-1]

                    if class_name not in class_index:
                        continue

                    candidate = class_index[class_name]

                    binding_rows.append(
                        {
                            "family": candidate.family,
                            "class_name": class_name,
                            "binding_type": type(value).__name__.upper(),
                            "path": relative,
                            "line": node.lineno,
                            "target": target,
                            "source": source_text(source, node),
                        }
                    )

    summary_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []

    for candidate in candidates:
        constructors = [
            row
            for row in constructor_rows
            if row["class_name"] == candidate.class_name
        ]

        bindings = [
            row
            for row in binding_rows
            if row["class_name"] == candidate.class_name
        ]

        calls = [
            row
            for row in class_call_rows
            if row["candidate_symbol"] == candidate.symbol
        ]

        interface_calls = [
            row
            for row in interface_rows
            if row["method"] == candidate.method
        ]

        evidence_count = (
            len(constructors)
            + len(bindings)
            + len(calls)
            + len(interface_calls)
        )

        classification = (
            "BINDING_EVIDENCE_FOUND"
            if evidence_count > 0
            else "NO_BINDING_EVIDENCE"
        )

        summary_rows.append(
            {
                "family": candidate.family,
                "candidate_symbol": candidate.symbol,
                "constructor_site_count": len(constructors),
                "binding_site_count": len(bindings),
                "class_method_call_count": len(calls),
                "interface_method_call_count": len(interface_calls),
                "evidence_count": evidence_count,
                "classification": classification,
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

        if evidence_count == 0:
            unresolved_rows.append(
                {
                    "family": candidate.family,
                    "candidate_symbol": candidate.symbol,
                    "reason": "NO_RUNTIME_BINDING_EVIDENCE",
                }
            )

    write_tsv(
        CONSTRUCTORS_FILE,
        ("family", "class_name", "path", "line", "call", "source"),
        constructor_rows,
    )
    write_tsv(
        BINDINGS_FILE,
        (
            "family",
            "class_name",
            "binding_type",
            "path",
            "line",
            "target",
            "source",
        ),
        binding_rows,
    )
    write_tsv(
        INTERFACE_CALLS_FILE,
        ("path", "line", "receiver", "method", "call", "source"),
        interface_rows,
    )
    write_tsv(
        CLASS_CALLS_FILE,
        (
            "family",
            "candidate_symbol",
            "path",
            "line",
            "call",
            "source",
        ),
        class_call_rows,
    )
    write_tsv(
        SUMMARY_FILE,
        (
            "family",
            "candidate_symbol",
            "constructor_site_count",
            "binding_site_count",
            "class_method_call_count",
            "interface_method_call_count",
            "evidence_count",
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

    print("=== AUDIT STRATEGY RUNTIME BINDING DISCOVERY V2 ===")
    print(f"candidate_count={len(candidates)}")
    print(f"constructor_site_count={len(constructor_rows)}")
    print(f"binding_site_count={len(binding_rows)}")
    print(f"interface_call_count={len(interface_rows)}")
    print(f"class_method_call_count={len(class_call_rows)}")
    print(
        "candidate_with_binding_evidence_count="
        f"{sum(row['evidence_count'] > 0 for row in summary_rows)}"
    )
    print(f"unresolved_count={len(unresolved_rows)}")

    for row in summary_rows:
        print(
            f"BINDING family={row['family']} "
            f"symbol={row['candidate_symbol']} "
            f"constructors={row['constructor_site_count']} "
            f"bindings={row['binding_site_count']} "
            f"class_calls={row['class_method_call_count']} "
            f"interface_calls={row['interface_method_call_count']} "
            f"class={row['classification']}"
        )

    print("confirmed_owner_count=0")
    print("owner_assignment_performed=0")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=STRATEGY_RUNTIME_BINDING_DISCOVERY_V2_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
