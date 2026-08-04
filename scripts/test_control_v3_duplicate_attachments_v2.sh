#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

RENDERER="$ROOT/src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py"

echo "=== TEST CONTROL V3 DUPLICATE ATTACHMENTS V2 ==="

[[ -f "$RENDERER" ]] || {
    echo "ERROR=renderer_missing:$RENDERER"
    exit 1
}

"$PYTHON" -m py_compile "$RENDERER"

PYTHONPATH="$ROOT/src" "$PYTHON" - <<'PY'
from __future__ import annotations

from collections import Counter
from typing import Any

import marketcore.presentation.workspace_v2.renderer.control_compact_v3_domain_renderer as renderer_module
from marketcore.presentation.workspace_v2.resolver.control_compact_v3_resolver import (
    ControlCompactV3Resolver,
)


HISTORICAL_ID = "control.v3.feature_store_historical_corrections"
OPEN_POSITIONS_ID = "control.v3.open_positions"


def read_attr(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def children_of(obj: Any) -> tuple[Any, ...]:
    children = read_attr(obj, "children", ())
    return tuple(children or ())


def node_id_of(obj: Any) -> str:
    return str(read_attr(obj, "node_id", "") or "")


original_validator = renderer_module.validate_render_document_v2


def bypass_validator(document: Any) -> Any:
    return document


renderer_module.validate_render_document_v2 = bypass_validator

try:
    snapshot = ControlCompactV3Resolver().resolve()

    document = renderer_module.render_control_compact_v3(
        snapshot,
        timezone_code="Europe/Moscow",
        document_id="operator.control.v3.duplicate-test-v2",
    )
finally:
    renderer_module.validate_render_document_v2 = original_validator


root = read_attr(document, "root")

if root is None:
    raise SystemExit("ERROR=document_root_missing")


rows: list[tuple[str, str]] = []


def visit(node: Any, path: str) -> None:
    node_id = node_id_of(node)

    if node_id:
        rows.append((path, node_id))

    for index, child in enumerate(children_of(node)):
        visit(child, f"{path}/children/{index}")


visit(root, "root")

counts = Counter(node_id for _, node_id in rows)

duplicates = {
    node_id: count
    for node_id, count in counts.items()
    if count > 1
}

historical_count = counts.get(HISTORICAL_ID, 0)
open_positions_count = counts.get(OPEN_POSITIONS_ID, 0)

print(f"full_tree_node_id_count={len(rows)}")
print(f"full_tree_unique_node_id_count={len(counts)}")
print(f"duplicate_node_id_count={len(duplicates)}")
print(f"historical_section_count={historical_count}")
print(f"open_positions_section_count={open_positions_count}")

for node_id, count in sorted(duplicates.items()):
    paths = [
        path
        for path, current_node_id in rows
        if current_node_id == node_id
    ]

    print(
        f"DUPLICATE id={node_id} "
        f"count={count} "
        f"paths={','.join(paths)}"
    )

if historical_count != 1:
    raise SystemExit(
        f"ERROR=historical_section_count:{historical_count}"
    )

if open_positions_count != 1:
    raise SystemExit(
        f"ERROR=open_positions_section_count:{open_positions_count}"
    )

if duplicates:
    raise SystemExit(
        "ERROR=full_tree_duplicate_node_ids:"
        + ",".join(sorted(duplicates))
    )

print("full_tree_uniqueness=OK")
print("duplicate_attachment_contract=OK")
PY

echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CONTROL_V3_DUPLICATE_ATTACHMENTS_V2_OK"
