#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

SEMANTIC_FILE = pathlib.Path(
    "/tmp/edge_semantic_classification_v1/"
    "authoritative_decision_candidates.tsv"
)

OUT = pathlib.Path(
    "/tmp/edge_runtime_reachability_sanity_v1"
)

CANDIDATES_FILE = OUT / "candidate_identities.tsv"
STRING_FILE = OUT / "string_references.tsv"
REGISTRY_FILE = OUT / "registry_references.tsv"
DYNAMIC_IMPORT_FILE = OUT / "dynamic_import_references.tsv"
GETATTR_FILE = OUT / "getattr_references.tsv"
CONFIG_FILE = OUT / "configuration_references.tsv"
EXECUTABLE_FILE = OUT / "executable_references.tsv"
SUMMARY_FILE = OUT / "candidate_summary.tsv"
EVIDENCE_FILE = OUT / "evidence.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

SCAN_ROOTS = (
    ROOT / "src",
    ROOT / "core",
    ROOT / "strategy",
    ROOT / "risk",
    ROOT / "config",
    ROOT / "scripts",
)

EXCLUDED_PREFIXES = (
    "scripts/audit_edge_",
    "scripts/test_edge_",
)

CANDIDATE_EXPECTED = {
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

REGISTRY_MARKERS = (
    "registry",
    "mapping",
    "map",
    "providers",
    "factories",
    "handlers",
    "plugins",
    "components",
    "strategies",
    "guards",
)

CONFIG_SUFFIXES = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".env",
    ".txt",
}

DYNAMIC_IMPORT_CALLS = {
    "importlib.import_module",
    "__import__",
}

REFLECTION_CALLS = {
    "getattr",
    "globals",
    "locals",
}


@dataclass(frozen=True, slots=True)
class Candidate:
    path: str
    class_name: str
    method: str
    symbol: str


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"source_missing:{path}")

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

    return ""


def source_text(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""

    try:
        return ast.get_source_segment(source, node) or ""
    except (IndexError, ValueError):
        return ""


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
        if row.get("semantic_classification")
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

    if actual != CANDIDATE_EXPECTED:
        raise RuntimeError(
            "candidate_identity_mismatch:"
            f"missing={sorted(CANDIDATE_EXPECTED - actual)}:"
            f"unexpected={sorted(actual - CANDIDATE_EXPECTED)}"
        )

    return sorted(
        candidates,
        key=lambda item: (
            item.path,
            item.symbol,
        ),
    )


def discover_files() -> list[pathlib.Path]:
    files: set[pathlib.Path] = set()

    for root in SCAN_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if "__pycache__" in path.parts:
                continue

            relative = str(path.resolve().relative_to(ROOT))

            if any(
                relative.startswith(prefix)
                for prefix in EXCLUDED_PREFIXES
            ):
                continue

            if (
                path.suffix == ".py"
                or path.suffix.lower() in CONFIG_SUFFIXES
            ):
                files.add(path.resolve())

    return sorted(files)


def literal_strings(node: ast.AST) -> list[str]:
    values: list[str] = []

    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.append(child.value)

    return values


def candidate_matches(
    text: str,
    candidate: Candidate,
) -> bool:
    return (
        candidate.class_name in text
        or candidate.symbol in text
        or candidate.path in text
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    candidates = load_candidates()

    candidate_rows = [
        {
            "candidate_path": candidate.path,
            "candidate_class": candidate.class_name,
            "candidate_method": candidate.method,
            "candidate_symbol": candidate.symbol,
        }
        for candidate in candidates
    ]

    string_rows: list[dict[str, object]] = []
    registry_rows: list[dict[str, object]] = []
    dynamic_rows: list[dict[str, object]] = []
    getattr_rows: list[dict[str, object]] = []
    config_rows: list[dict[str, object]] = []
    executable_rows: list[dict[str, object]] = []
    unresolved_rows: list[dict[str, object]] = []

    for path in discover_files():
        relative = str(path.relative_to(ROOT))
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        if path.suffix != ".py":
            for line_number, line in enumerate(
                source.splitlines(),
                start=1,
            ):
                for candidate in candidates:
                    if candidate_matches(line, candidate):
                        config_rows.append(
                            {
                                "candidate_symbol": candidate.symbol,
                                "path": relative,
                                "line": line_number,
                                "reference": line.strip(),
                                "classification": "CONFIGURATION_REFERENCE",
                            }
                        )
            continue

        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            unresolved_rows.append(
                {
                    "scope": "SOURCE_PARSE",
                    "candidate_symbol": "",
                    "path": relative,
                    "reason": str(exc),
                }
            )
            continue

        parent_stack: list[ast.AST] = []

        class Visitor(ast.NodeVisitor):
            def generic_visit(self, node: ast.AST) -> None:
                parent_stack.append(node)
                super().generic_visit(node)
                parent_stack.pop()

            def visit_Constant(self, node: ast.Constant) -> None:
                if isinstance(node.value, str):
                    for candidate in candidates:
                        if candidate_matches(node.value, candidate):
                            string_rows.append(
                                {
                                    "candidate_symbol": candidate.symbol,
                                    "path": relative,
                                    "line": getattr(node, "lineno", 0),
                                    "reference": node.value,
                                    "classification": "STRING_REFERENCE",
                                }
                            )

                self.generic_visit(node)

            def visit_Dict(self, node: ast.Dict) -> None:
                dict_source = source_text(source, node)
                parent_source = " ".join(
                    source_text(source, parent)
                    for parent in parent_stack[-3:]
                )

                context = f"{parent_source} {dict_source}".lower()

                if not any(marker in context for marker in REGISTRY_MARKERS):
                    self.generic_visit(node)
                    return

                for candidate in candidates:
                    if candidate_matches(dict_source, candidate):
                        registry_rows.append(
                            {
                                "candidate_symbol": candidate.symbol,
                                "path": relative,
                                "line": node.lineno,
                                "registry_context": parent_source.strip(),
                                "reference": dict_source,
                                "classification": "REGISTRY_OR_MAPPING_REFERENCE",
                            }
                        )

                self.generic_visit(node)

            def visit_Call(self, node: ast.Call) -> None:
                call = dotted_name(node.func)
                call_source = source_text(source, node)
                strings = literal_strings(node)

                if call in DYNAMIC_IMPORT_CALLS:
                    for candidate in candidates:
                        if any(
                            candidate_matches(value, candidate)
                            for value in strings
                        ):
                            dynamic_rows.append(
                                {
                                    "candidate_symbol": candidate.symbol,
                                    "path": relative,
                                    "line": node.lineno,
                                    "call": call,
                                    "reference": call_source,
                                    "classification": "DYNAMIC_IMPORT_REFERENCE",
                                }
                            )

                if call in REFLECTION_CALLS:
                    for candidate in candidates:
                        if any(
                            candidate_matches(value, candidate)
                            for value in strings
                        ):
                            getattr_rows.append(
                                {
                                    "candidate_symbol": candidate.symbol,
                                    "path": relative,
                                    "line": node.lineno,
                                    "call": call,
                                    "reference": call_source,
                                    "classification": "REFLECTION_REFERENCE",
                                }
                            )

                # Прямой вызов конструктора или статический вызов класса.
                terminal = call.rsplit(".", 1)[-1]

                for candidate in candidates:
                    direct_constructor = terminal == candidate.class_name
                    direct_class_call = call.startswith(
                        f"{candidate.class_name}."
                    )

                    if direct_constructor or direct_class_call:
                        executable_rows.append(
                            {
                                "candidate_symbol": candidate.symbol,
                                "path": relative,
                                "line": node.lineno,
                                "call": call,
                                "reference": call_source,
                                "classification": (
                                    "DIRECT_CONSTRUCTION"
                                    if direct_constructor
                                    else "DIRECT_CLASS_METHOD_CALL"
                                ),
                            }
                        )

                self.generic_visit(node)

        Visitor().visit(tree)

    summary_rows: list[dict[str, object]] = []

    for candidate in candidates:
        string_count = sum(
            row["candidate_symbol"] == candidate.symbol
            for row in string_rows
        )
        registry_count = sum(
            row["candidate_symbol"] == candidate.symbol
            for row in registry_rows
        )
        dynamic_count = sum(
            row["candidate_symbol"] == candidate.symbol
            for row in dynamic_rows
        )
        reflection_count = sum(
            row["candidate_symbol"] == candidate.symbol
            for row in getattr_rows
        )
        config_count = sum(
            row["candidate_symbol"] == candidate.symbol
            for row in config_rows
        )
        executable_count = sum(
            row["candidate_symbol"] == candidate.symbol
            for row in executable_rows
        )

        indirect_reference_count = (
            registry_count
            + dynamic_count
            + reflection_count
            + config_count
        )

        if executable_count > 0:
            classification = "EXECUTABLE_REFERENCE_FOUND"
        elif indirect_reference_count > 0:
            classification = "INDIRECT_RUNTIME_REFERENCE_CANDIDATE"
        elif string_count > 0:
            classification = "NON_EXECUTABLE_STRING_REFERENCE_ONLY"
        else:
            classification = "NO_RUNTIME_REFERENCE_FOUND"

        summary_rows.append(
            {
                "candidate_path": candidate.path,
                "candidate_symbol": candidate.symbol,
                "string_reference_count": string_count,
                "registry_reference_count": registry_count,
                "dynamic_import_count": dynamic_count,
                "reflection_reference_count": reflection_count,
                "configuration_reference_count": config_count,
                "executable_reference_count": executable_count,
                "classification": classification,
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    write_tsv(
        CANDIDATES_FILE,
        (
            "candidate_path",
            "candidate_class",
            "candidate_method",
            "candidate_symbol",
        ),
        candidate_rows,
    )

    write_tsv(
        STRING_FILE,
        (
            "candidate_symbol",
            "path",
            "line",
            "reference",
            "classification",
        ),
        string_rows,
    )

    write_tsv(
        REGISTRY_FILE,
        (
            "candidate_symbol",
            "path",
            "line",
            "registry_context",
            "reference",
            "classification",
        ),
        registry_rows,
    )

    write_tsv(
        DYNAMIC_IMPORT_FILE,
        (
            "candidate_symbol",
            "path",
            "line",
            "call",
            "reference",
            "classification",
        ),
        dynamic_rows,
    )

    write_tsv(
        GETATTR_FILE,
        (
            "candidate_symbol",
            "path",
            "line",
            "call",
            "reference",
            "classification",
        ),
        getattr_rows,
    )

    write_tsv(
        CONFIG_FILE,
        (
            "candidate_symbol",
            "path",
            "line",
            "reference",
            "classification",
        ),
        config_rows,
    )

    write_tsv(
        EXECUTABLE_FILE,
        (
            "candidate_symbol",
            "path",
            "line",
            "call",
            "reference",
            "classification",
        ),
        executable_rows,
    )

    write_tsv(
        SUMMARY_FILE,
        (
            "candidate_path",
            "candidate_symbol",
            "string_reference_count",
            "registry_reference_count",
            "dynamic_import_count",
            "reflection_reference_count",
            "configuration_reference_count",
            "executable_reference_count",
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
            "candidate_symbol",
            "path",
            "reason",
        ),
        unresolved_rows,
    )

    with EVIDENCE_FILE.open("w", encoding="utf-8") as stream:
        stream.write("EDGE RUNTIME REACHABILITY SANITY V1\n")
        stream.write("===================================\n\n")

        for row in summary_rows:
            stream.write(
                f"CANDIDATE symbol={row['candidate_symbol']} "
                f"strings={row['string_reference_count']} "
                f"registries={row['registry_reference_count']} "
                f"dynamic_imports={row['dynamic_import_count']} "
                f"reflection={row['reflection_reference_count']} "
                f"config={row['configuration_reference_count']} "
                f"executable={row['executable_reference_count']} "
                f"class={row['classification']}\n"
            )

    print("=== AUDIT EDGE RUNTIME REACHABILITY SANITY V1 ===")
    print(f"candidate_count={len(candidates)}")
    print(f"string_reference_count={len(string_rows)}")
    print(f"registry_reference_count={len(registry_rows)}")
    print(f"dynamic_import_count={len(dynamic_rows)}")
    print(f"reflection_reference_count={len(getattr_rows)}")
    print(f"configuration_reference_count={len(config_rows)}")
    print(f"executable_reference_count={len(executable_rows)}")
    print(f"unresolved_count={len(unresolved_rows)}")

    for row in summary_rows:
        print(
            "SANITY "
            f"symbol={row['candidate_symbol']} "
            f"strings={row['string_reference_count']} "
            f"registries={row['registry_reference_count']} "
            f"dynamic_imports={row['dynamic_import_count']} "
            f"reflection={row['reflection_reference_count']} "
            f"config={row['configuration_reference_count']} "
            f"executable={row['executable_reference_count']} "
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
    print("VERDICT=EDGE_RUNTIME_REACHABILITY_SANITY_V1_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
