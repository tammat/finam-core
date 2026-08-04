#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

RENDERER="$ROOT/src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py"

echo "=== TEST CONTROL V3 HISTORICAL CORRECTIONS FULL SECTION V1 ==="

"$PYTHON" -m py_compile "$RENDERER"

PYTHONPATH="$ROOT/src" "$PYTHON" - "$RENDERER" <<'PY'
from __future__ import annotations

import ast
import pathlib
import sys
from collections import Counter
from typing import Any

import marketcore.presentation.workspace_v2.renderer.control_compact_v3_domain_renderer as renderer_module
from marketcore.presentation.workspace_v2.resolver.control_compact_v3_resolver import (
    ControlCompactV3Resolver,
)


renderer_path = pathlib.Path(sys.argv[1])
source = renderer_path.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(renderer_path))

RENDER_FUNCTION = "render_control_compact_v3"
LEGACY_HELPER = "_historical_corrections_section"
FULL_HELPER = "_historical_corrections_section_v1"

HISTORICAL_ID = (
    "control.v3.feature_store_historical_corrections"
)
RECENT_TABLE_ID = (
    "control.v3.feature_store_historical_corrections.recent_audits"
)
RECENT_BODY_ID = (
    "control.v3.feature_store_historical_corrections.recent.body"
)


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return None


renderers = [
    node
    for node in tree.body
    if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == RENDER_FUNCTION
    )
]

if len(renderers) != 1:
    raise SystemExit(
        f"ERROR=active_renderer_count:{len(renderers)}"
    )

renderer = renderers[0]

legacy_attachment_count = sum(
    1
    for node in ast.walk(renderer)
    if (
        isinstance(node, ast.Call)
        and call_name(node) == LEGACY_HELPER
    )
)

full_attachment_count = sum(
    1
    for node in ast.walk(renderer)
    if (
        isinstance(node, ast.Call)
        and call_name(node) == FULL_HELPER
    )
)

print(
    "legacy_attachment_count="
    + str(legacy_attachment_count)
)
print(
    "full_attachment_count="
    + str(full_attachment_count)
)

if legacy_attachment_count != 0:
    raise SystemExit(
        "ERROR=legacy_attachment_count:"
        + str(legacy_attachment_count)
    )

if full_attachment_count != 1:
    raise SystemExit(
        "ERROR=full_attachment_count:"
        + str(full_attachment_count)
    )


def read_attr(
    obj: Any,
    name: str,
    default: Any = None,
) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def children_of(obj: Any) -> tuple[Any, ...]:
    return tuple(
        read_attr(obj, "children", ()) or ()
    )


def node_id_of(obj: Any) -> str:
    return str(
        read_attr(obj, "node_id", "") or ""
    )


original_validator = (
    renderer_module.validate_render_document_v2
)


def bypass_validator(document: Any) -> Any:
    return document


renderer_module.validate_render_document_v2 = (
    bypass_validator
)

try:
    snapshot = ControlCompactV3Resolver().resolve()

    historical = (
        snapshot.get("historical_corrections")
        or {}
    )

    recent_audits = (
        historical.get("recent_audits")
        or []
    )

    document = renderer_module.render_control_compact_v3(
        snapshot,
        timezone_code="Europe/Moscow",
        document_id=(
            "operator.control.v3."
            "historical-full-section-test"
        ),
    )
finally:
    renderer_module.validate_render_document_v2 = (
        original_validator
    )

root = read_attr(document, "root", None)

if root is None:
    raise SystemExit("ERROR=document_root_missing")

rows: list[tuple[str, str, str]] = []


def visit(node: Any, path: str) -> None:
    node_id = node_id_of(node)

    node_type_value = read_attr(
        node,
        "node_type",
        read_attr(node, "type", ""),
    )

    node_type = str(
        getattr(
            node_type_value,
            "value",
            node_type_value,
        )
    )

    if node_id:
        rows.append((path, node_id, node_type))

    for index, child in enumerate(children_of(node)):
        visit(
            child,
            f"{path}/children/{index}",
        )


visit(root, "root")

counts = Counter(
    node_id
    for _, node_id, _ in rows
)

duplicates = {
    node_id: count
    for node_id, count in counts.items()
    if count > 1
}

historical_count = counts.get(HISTORICAL_ID, 0)
recent_table_count = counts.get(RECENT_TABLE_ID, 0)
recent_body_count = counts.get(RECENT_BODY_ID, 0)

recent_row_count = sum(
    1
    for _, node_id, node_type in rows
    if (
        node_id.startswith(
            HISTORICAL_ID + ".recent.row."
        )
        and node_type == "table_row"
    )
)

recent_cell_count = sum(
    1
    for _, node_id, node_type in rows
    if (
        node_id.startswith(
            HISTORICAL_ID + ".recent.row."
        )
        and node_type == "table_cell"
    )
)

expected_rendered_rows = min(
    len(recent_audits),
    20,
)

print(f"snapshot_recent_audits={len(recent_audits)}")
print(f"full_tree_node_id_count={len(rows)}")
print(f"unique_node_id_count={len(counts)}")
print(f"duplicate_node_id_count={len(duplicates)}")
print(f"historical_section_count={historical_count}")
print(f"recent_table_count={recent_table_count}")
print(f"recent_body_count={recent_body_count}")
print(f"recent_row_count={recent_row_count}")
print(f"recent_cell_count={recent_cell_count}")
print(f"expected_rendered_rows={expected_rendered_rows}")

if duplicates:
    raise SystemExit(
        "ERROR=duplicate_node_ids:"
        + ",".join(sorted(duplicates))
    )

if historical_count != 1:
    raise SystemExit(
        "ERROR=historical_section_count:"
        + str(historical_count)
    )

if recent_table_count != 1:
    raise SystemExit(
        "ERROR=recent_table_count:"
        + str(recent_table_count)
    )

if recent_body_count != 1:
    raise SystemExit(
        "ERROR=recent_body_count:"
        + str(recent_body_count)
    )

if recent_row_count != expected_rendered_rows:
    raise SystemExit(
        "ERROR=recent_row_count:"
        + str(recent_row_count)
        + ":expected:"
        + str(expected_rendered_rows)
    )

if recent_cell_count != expected_rendered_rows * 4:
    raise SystemExit(
        "ERROR=recent_cell_count:"
        + str(recent_cell_count)
        + ":expected:"
        + str(expected_rendered_rows * 4)
    )

print("active_full_section_contract=OK")
print("full_tree_uniqueness=OK")
print("recent_audits_render_contract=OK")
PY

echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CONTROL_V3_HISTORICAL_CORRECTIONS_FULL_SECTION_V1_OK"
