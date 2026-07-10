from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRESENTATION_ROOT = PROJECT_ROOT / "src/marketcore/presentation"
RENDER_TREE_ROOT = PRESENTATION_ROOT / "render_tree"

PLATFORM_NODE_TYPES = {
    "main",
    "section",
    "header",
    "article",
    "div",
    "h1",
    "h2",
    "h3",
    "p",
    "a",
    "dl",
    "dt",
    "dd",
}


def python_files(root: Path) -> tuple[Path, ...]:
    if not root.exists():
        return ()

    return tuple(
        sorted(
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts
        )
    )


def relative(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT))


def render_node_types(path: Path) -> list[tuple[int, str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    found: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        function_name = ""

        if isinstance(node.func, ast.Name):
            function_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            function_name = node.func.attr

        if function_name != "RenderNode":
            continue

        value_node: ast.AST | None = None

        if node.args:
            value_node = node.args[0]

        for keyword in node.keywords:
            if keyword.arg == "node_type":
                value_node = keyword.value
                break

        if isinstance(value_node, ast.Constant) and isinstance(value_node.value, str):
            found.append((node.lineno, value_node.value))
        elif isinstance(value_node, ast.Attribute):
            parts: list[str] = []
            current: ast.AST = value_node

            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value

            if isinstance(current, ast.Name):
                parts.append(current.id)

            found.append((node.lineno, ".".join(reversed(parts))))

    return found


def text_references(patterns: tuple[str, ...]) -> list[tuple[str, int, str]]:
    rows: list[tuple[str, int, str]] = []

    for path in python_files(PRESENTATION_ROOT):
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if any(pattern in line for pattern in patterns):
                rows.append((relative(path), line_number, line.strip()))

    return rows


def main() -> None:
    presentation_files = python_files(PRESENTATION_ROOT)
    render_tree_files = python_files(RENDER_TREE_ROOT)

    node_rows: list[tuple[str, int, str]] = []

    for path in presentation_files:
        for line_number, node_type in render_node_types(path):
            node_rows.append((relative(path), line_number, node_type))

    node_counter = Counter(node_type for _, _, node_type in node_rows)

    platform_rows = [
        row
        for row in node_rows
        if row[2].lower() in PLATFORM_NODE_TYPES
    ]

    legacy_rows = text_references(
        (
            "HtmlAdapter",
            "render_tree.html_adapter",
            "WebRenderer",
            "render_engine.web_renderer",
        )
    )

    render_tree_platform_terms = []

    for path in render_tree_files:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            lowered = line.lower()

            if any(
                term in lowered
                for term in (
                    "html",
                    "web",
                    "css",
                    "http",
                )
            ):
                render_tree_platform_terms.append(
                    (relative(path), line_number, line.strip())
                )

    print("======================================================")
    print("MARKETCORE_RENDER_TREE_DOMAIN_INVENTORY_V1")
    print("======================================================")

    print()
    print("RENDER_TREE_FILES")
    for path in render_tree_files:
        print(relative(path))

    print()
    print("NODE_TYPES_FILE")
    node_types_file = RENDER_TREE_ROOT / "node_types.py"
    print(
        relative(node_types_file)
        if node_types_file.exists()
        else "NODE_TYPES_FILE_NOT_FOUND"
    )

    print()
    print("CURRENT_NODE_TYPES")
    for node_type, count in sorted(node_counter.items()):
        print(f"NODE_TYPE name={node_type} count={count}")

    print()
    print("PLATFORM_NODE_TYPE_USAGE")
    if platform_rows:
        for path, line_number, node_type in platform_rows:
            print(
                f"PLATFORM_NODE "
                f"file={path} "
                f"line={line_number} "
                f"type={node_type}"
            )
    else:
        print("PLATFORM_NODE_TYPE_USAGE=0")

    print()
    print("LEGACY_RENDER_REFERENCES")
    if legacy_rows:
        for path, line_number, line in legacy_rows:
            print(
                f"LEGACY_REFERENCE "
                f"file={path} "
                f"line={line_number} "
                f"text={line}"
            )
    else:
        print("LEGACY_RENDER_REFERENCES=0")

    print()
    print("PLATFORM_TERMS_INSIDE_RENDER_TREE")
    if render_tree_platform_terms:
        for path, line_number, line in render_tree_platform_terms:
            print(
                f"PLATFORM_TERM "
                f"file={path} "
                f"line={line_number} "
                f"text={line}"
            )
    else:
        print("PLATFORM_TERMS_INSIDE_RENDER_TREE=0")

    print()
    print(f"presentation_python_files={len(presentation_files)}")
    print(f"render_tree_python_files={len(render_tree_files)}")
    print(f"render_node_calls={len(node_rows)}")
    print(f"unique_node_types={len(node_counter)}")
    print(f"platform_node_usages={len(platform_rows)}")
    print(f"legacy_render_references={len(legacy_rows)}")
    print(
        "platform_terms_inside_render_tree="
        f"{len(render_tree_platform_terms)}"
    )

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_RENDER_TREE_DOMAIN_INVENTORY_V1_READY")


if __name__ == "__main__":
    main()
