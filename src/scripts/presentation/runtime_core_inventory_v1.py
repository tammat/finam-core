from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
MARKETCORE_ROOT = SRC_ROOT / "marketcore"
PRESENTATION_ROOT = MARKETCORE_ROOT / "presentation"

PYTHON_SUFFIX = ".py"
JAVASCRIPT_SUFFIXES = {".js", ".mjs", ".cjs"}

RUNTIME_NAME_MARKERS = (
    "runtime",
    "driver",
    "platform",
    "render_tree",
    "renderer",
    "adapter",
)

RUNTIME_SYMBOL_MARKERS = (
    "Runtime",
    "RuntimeCore",
    "PlatformDriver",
    "RenderTree",
    "RenderDocument",
    "RenderNode",
    "validate",
    "driver",
    "mount",
    "render",
)

DELIVERY_MARKERS = (
    "route(",
    "send_response",
    "send_header",
    "Content-Type",
    "application/json",
    "/api/v1/render-tree/",
    "/assets/marketcore/ui-runtime/",
)

FORBIDDEN_CORE_MARKERS = (
    "psycopg",
    "SELECT ",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "send_order",
    "place_order",
    "cancel_order",
    "execute_order",
    "innerHTML",
    "document.createElement",
    "fetch(",
    "XMLHttpRequest",
    "<main",
    "<div",
    "<article",
)


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def source_files() -> tuple[Path, ...]:
    if not SRC_ROOT.exists():
        return ()

    return tuple(
        sorted(
            path
            for path in SRC_ROOT.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and (
                path.suffix == PYTHON_SUFFIX
                or path.suffix in JAVASCRIPT_SUFFIXES
            )
        )
    )


def candidate_files(
    files: tuple[Path, ...],
) -> tuple[Path, ...]:
    candidates: list[Path] = []

    for path in files:
        lowered = relative(path).lower()

        if any(marker in lowered for marker in RUNTIME_NAME_MARKERS):
            candidates.append(path)

    return tuple(candidates)


def read_lines(path: Path) -> tuple[str, ...]:
    try:
        return tuple(
            path.read_text(encoding="utf-8").splitlines()
        )
    except UnicodeDecodeError:
        return ()


def marker_rows(
    files: tuple[Path, ...],
    markers: tuple[str, ...],
) -> list[tuple[str, int, str, str]]:
    rows: list[tuple[str, int, str, str]] = []

    for path in files:
        for line_number, line in enumerate(
            read_lines(path),
            start=1,
        ):
            for marker in markers:
                if marker in line:
                    rows.append(
                        (
                            relative(path),
                            line_number,
                            marker,
                            line.strip(),
                        )
                    )

    return rows


def python_symbols(
    files: tuple[Path, ...],
) -> list[tuple[str, int, str, str]]:
    rows: list[tuple[str, int, str, str]] = []

    for path in files:
        if path.suffix != ".py":
            continue

        source = path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            rows.append(
                (
                    relative(path),
                    exc.lineno or 0,
                    "SYNTAX_ERROR",
                    str(exc),
                )
            )
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                kind = "CLASS"
                name = node.name
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "FUNCTION"
                name = node.name
            else:
                continue

            if any(
                marker.lower() in name.lower()
                for marker in RUNTIME_SYMBOL_MARKERS
            ):
                rows.append(
                    (
                        relative(path),
                        node.lineno,
                        kind,
                        name,
                    )
                )

    return rows


def import_rows(
    files: tuple[Path, ...],
) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []

    for path in files:
        if path.suffix != ".py":
            continue

        source = path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            module_name = ""

            if isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
            elif isinstance(node, ast.Import):
                module_name = ",".join(
                    alias.name
                    for alias in node.names
                )

            if any(
                marker in module_name.lower()
                for marker in (
                    "render_tree",
                    "ui_runtime",
                    "driver",
                    "adapter",
                    "renderer",
                )
            ):
                rows.append(
                    (
                        relative(path),
                        node.lineno,
                        module_name,
                    )
                )

    return rows


def print_marker_rows(
    title: str,
    rows: list[tuple[str, int, str, str]],
) -> None:
    print()
    print(title)

    if not rows:
        print(f"{title}=0")
        return

    for path, line_number, marker, text in rows:
        print(
            "MATCH "
            f"file={path} "
            f"line={line_number} "
            f"marker={marker!r} "
            f"text={text}"
        )


def main() -> None:
    files = source_files()
    candidates = candidate_files(files)

    symbols = python_symbols(candidates)
    imports = import_rows(files)

    delivery_rows = marker_rows(
        candidates,
        DELIVERY_MARKERS,
    )
    forbidden_rows = marker_rows(
        candidates,
        FORBIDDEN_CORE_MARKERS,
    )

    suffix_counts = Counter(
        path.suffix
        for path in candidates
    )

    runtime_core_candidates = tuple(
        path
        for path in candidates
        if any(
            marker in relative(path).lower()
            for marker in (
                "runtime_core",
                "/runtime/",
                "runtime_v",
                "ui_runtime",
            )
        )
    )

    driver_candidates = tuple(
        path
        for path in candidates
        if "driver" in relative(path).lower()
    )

    print("======================================================")
    print("MARKETCORE_RUNTIME_CORE_INVENTORY_V1")
    print("======================================================")

    print()
    print("CANDIDATE_FILE_COUNTS")
    for suffix, count in sorted(suffix_counts.items()):
        print(f"FILE_TYPE suffix={suffix} count={count}")

    print()
    print("RUNTIME_RELATED_FILES")
    if candidates:
        for path in candidates:
            print(relative(path))
    else:
        print("RUNTIME_RELATED_FILES=0")

    print()
    print("RUNTIME_CORE_CANDIDATES")
    if runtime_core_candidates:
        for path in runtime_core_candidates:
            print(relative(path))
    else:
        print("RUNTIME_CORE_CANDIDATES=0")

    print()
    print("PLATFORM_DRIVER_CANDIDATES")
    if driver_candidates:
        for path in driver_candidates:
            print(relative(path))
    else:
        print("PLATFORM_DRIVER_CANDIDATES=0")

    print()
    print("RUNTIME_RELATED_SYMBOLS")
    if symbols:
        for path, line_number, kind, name in symbols:
            print(
                f"SYMBOL file={path} "
                f"line={line_number} "
                f"kind={kind} "
                f"name={name}"
            )
    else:
        print("RUNTIME_RELATED_SYMBOLS=0")

    print()
    print("RENDER_TREE_RUNTIME_IMPORTS")
    if imports:
        for path, line_number, module_name in imports:
            print(
                f"IMPORT file={path} "
                f"line={line_number} "
                f"module={module_name}"
            )
    else:
        print("RENDER_TREE_RUNTIME_IMPORTS=0")

    print_marker_rows(
        "DELIVERY_DEPENDENCY_MARKERS",
        delivery_rows,
    )
    print_marker_rows(
        "FORBIDDEN_RUNTIME_CORE_MARKERS",
        forbidden_rows,
    )

    runtime_core_found = int(
        bool(runtime_core_candidates)
    )
    platform_driver_found = int(
        bool(driver_candidates)
    )

    print()
    print("ANALYSIS_INPUTS")
    print(f"runtime_core_candidate_files={len(runtime_core_candidates)}")
    print(f"platform_driver_candidate_files={len(driver_candidates)}")
    print(f"runtime_related_symbols={len(symbols)}")
    print(f"runtime_related_imports={len(imports)}")
    print(f"delivery_dependency_rows={len(delivery_rows)}")
    print(f"forbidden_core_marker_rows={len(forbidden_rows)}")
    print(f"runtime_core_found={runtime_core_found}")
    print(f"platform_driver_found={platform_driver_found}")

    print()
    print("DECISION_PENDING")
    print("inventory_only=1")
    print("runtime_core_created=0")
    print("platform_driver_created=0")
    print("architecture_changed=0")

    print()
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "MARKETCORE_RUNTIME_CORE_INVENTORY_V1_READY"
    )


if __name__ == "__main__":
    main()
