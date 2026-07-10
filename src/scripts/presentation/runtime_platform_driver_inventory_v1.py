from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MARKETCORE_ROOT = PROJECT_ROOT / "src" / "marketcore"
RUNTIME_ROOT = MARKETCORE_ROOT / "runtime"

DRIVER_REQUIRED_METHODS = frozenset(
    {
        "begin_document",
        "render_node",
        "end_document",
    }
)

EXCLUDED_PATH_PARTS = frozenset(
    {
        "__pycache__",
        "scripts",
        "tests",
        "generated",
        "proto",
    }
)

PLATFORM_TERMS = (
    "html",
    "dom",
    "browser",
    "web",
    "desktop",
    "terminal",
    "pdf",
    "flutter",
    "canvas",
    "driver",
)


@dataclass(frozen=True, slots=True)
class ClassCandidateV1:
    file_name: str
    line_number: int
    class_name: str
    methods: frozenset[str]
    base_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class JavascriptCandidateV1:
    file_name: str
    matched_terms: tuple[str, ...]


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def is_excluded(path: Path) -> bool:
    return bool(EXCLUDED_PATH_PARTS.intersection(path.parts))


def python_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in MARKETCORE_ROOT.rglob("*.py")
            if not is_excluded(path)
        )
    )


def javascript_files() -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in MARKETCORE_ROOT.rglob("*")
            if path.is_file()
            and not is_excluded(path)
            and path.suffix.lower() in {".js", ".mjs", ".cjs"}
        )
    )


def expression_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.expr = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    if isinstance(node, ast.Subscript):
        return expression_name(node.value)

    return ""


def class_candidates(
    files: tuple[Path, ...],
) -> tuple[ClassCandidateV1, ...]:
    rows: list[ClassCandidateV1] = []

    for path in files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            method_names = frozenset(
                child.name
                for child in node.body
                if isinstance(
                    child,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                )
            )

            base_names = tuple(
                name
                for base in node.bases
                if (name := expression_name(base))
            )

            references_protocol = any(
                base_name.endswith("PlatformDriverV1")
                for base_name in base_names
            )

            structurally_complete = (
                DRIVER_REQUIRED_METHODS
                <= method_names
            )

            class_name_suggests_driver = (
                "driver" in node.name.lower()
            )

            if (
                references_protocol
                or structurally_complete
                or class_name_suggests_driver
            ):
                rows.append(
                    ClassCandidateV1(
                        file_name=relative(path),
                        line_number=node.lineno,
                        class_name=node.name,
                        methods=method_names,
                        base_names=base_names,
                    )
                )

    return tuple(rows)


def javascript_candidates(
    files: tuple[Path, ...],
) -> tuple[JavascriptCandidateV1, ...]:
    rows: list[JavascriptCandidateV1] = []

    for path in files:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        lowered = source.lower()

        matched_terms = tuple(
            sorted(
                {
                    term
                    for term in PLATFORM_TERMS
                    if term in lowered
                }
            )
        )

        has_driver_lifecycle = all(
            method in source
            for method in DRIVER_REQUIRED_METHODS
        )

        path_suggests_driver = (
            "driver" in relative(path).lower()
        )

        if (
            has_driver_lifecycle
            or path_suggests_driver
        ):
            rows.append(
                JavascriptCandidateV1(
                    file_name=relative(path),
                    matched_terms=matched_terms,
                )
            )

    return tuple(rows)


def imported_platform_driver_files(
    files: tuple[Path, ...],
) -> tuple[str, ...]:
    rows: set[str] = set()

    for path in files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported_names = {
                    alias.name
                    for alias in node.names
                }

                if "PlatformDriverV1" in imported_names:
                    rows.add(relative(path))

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if "platform_driver_v1" in alias.name:
                        rows.add(relative(path))

    return tuple(sorted(rows))


def main() -> None:
    py_files = python_files()
    js_files = javascript_files()

    class_rows = class_candidates(py_files)
    js_rows = javascript_candidates(js_files)
    import_rows = imported_platform_driver_files(py_files)

    production_class_rows = tuple(
        row
        for row in class_rows
        if row.file_name
        != "src/marketcore/runtime/platform_driver_v1.py"
    )

    complete_python_drivers = tuple(
        row
        for row in production_class_rows
        if DRIVER_REQUIRED_METHODS <= row.methods
    )

    explicit_protocol_implementations = tuple(
        row
        for row in production_class_rows
        if any(
            base_name.endswith("PlatformDriverV1")
            for base_name in row.base_names
        )
    )

    platform_driver_found = int(
        bool(
            complete_python_drivers
            or explicit_protocol_implementations
            or js_rows
        )
    )

    print("======================================================")
    print("MARKETCORE_RUNTIME_PLATFORM_DRIVER_INVENTORY_V1")
    print("======================================================")

    print()
    print("PLATFORM_DRIVER_PROTOCOL")
    protocol_path = (
        RUNTIME_ROOT / "platform_driver_v1.py"
    )

    if protocol_path.exists():
        print(relative(protocol_path))
    else:
        print("PLATFORM_DRIVER_PROTOCOL_NOT_FOUND")

    print()
    print("PYTHON_DRIVER_CLASS_CANDIDATES")
    if production_class_rows:
        for row in production_class_rows:
            print(
                "CLASS "
                f"file={row.file_name} "
                f"line={row.line_number} "
                f"name={row.class_name} "
                f"bases={','.join(row.base_names) or '-'} "
                f"methods={','.join(sorted(row.methods)) or '-'}"
            )
    else:
        print("PYTHON_DRIVER_CLASS_CANDIDATES=0")

    print()
    print("COMPLETE_PYTHON_PLATFORM_DRIVERS")
    if complete_python_drivers:
        for row in complete_python_drivers:
            print(
                "DRIVER "
                f"file={row.file_name} "
                f"line={row.line_number} "
                f"name={row.class_name}"
            )
    else:
        print("COMPLETE_PYTHON_PLATFORM_DRIVERS=0")

    print()
    print("EXPLICIT_PLATFORM_DRIVER_IMPLEMENTATIONS")
    if explicit_protocol_implementations:
        for row in explicit_protocol_implementations:
            print(
                "IMPLEMENTATION "
                f"file={row.file_name} "
                f"line={row.line_number} "
                f"name={row.class_name}"
            )
    else:
        print(
            "EXPLICIT_PLATFORM_DRIVER_IMPLEMENTATIONS=0"
        )

    print()
    print("PLATFORM_DRIVER_IMPORTS")
    if import_rows:
        for file_name in import_rows:
            print(file_name)
    else:
        print("PLATFORM_DRIVER_IMPORTS=0")

    print()
    print("JAVASCRIPT_DRIVER_CANDIDATES")
    if js_rows:
        for row in js_rows:
            print(
                "JS_DRIVER "
                f"file={row.file_name} "
                f"terms={','.join(row.matched_terms) or '-'}"
            )
    else:
        print("JAVASCRIPT_DRIVER_CANDIDATES=0")

    print()
    print("ANALYSIS_INPUTS")
    print(f"python_files_scanned={len(py_files)}")
    print(f"javascript_files_scanned={len(js_files)}")
    print(
        "python_driver_class_candidates="
        f"{len(production_class_rows)}"
    )
    print(
        "complete_python_platform_drivers="
        f"{len(complete_python_drivers)}"
    )
    print(
        "explicit_platform_driver_implementations="
        f"{len(explicit_protocol_implementations)}"
    )
    print(
        "platform_driver_import_files="
        f"{len(import_rows)}"
    )
    print(
        "javascript_driver_candidates="
        f"{len(js_rows)}"
    )
    print(
        f"platform_driver_found={platform_driver_found}"
    )

    print()
    print("DECISION")

    if platform_driver_found:
        print(
            "next_step="
            "MARKETCORE_RUNTIME_PLATFORM_DRIVER_EXISTING_"
            "IMPLEMENTATION_ANALYSIS_V1"
        )
    else:
        print(
            "next_step="
            "MARKETCORE_RUNTIME_PLATFORM_DRIVER_CONTRACT_V1"
        )

    print()
    print("inventory_only=1")
    print("platform_driver_created=0")
    print("runtime_core_changed=0")
    print("architecture_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "MARKETCORE_RUNTIME_PLATFORM_DRIVER_INVENTORY_V1_READY"
    )


if __name__ == "__main__":
    main()
