#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

ENDPOINT="http://127.0.0.1:8080/api/v2/domain-render-tree/control-center"
BODY="/tmp/marketcore_ui_historical_corrections_recent_audits_shape_v1.json"

echo "=== AUDIT MARKETCORE UI HISTORICAL CORRECTIONS RECENT AUDITS SHAPE V1 ==="

HTTP_STATUS="$(
    curl \
        --silent \
        --show-error \
        --output "$BODY" \
        --write-out '%{http_code}' \
        "$ENDPOINT"
)"

echo "render_tree_http_status=$HTTP_STATUS"
echo "response_file=$BODY"

[[ "$HTTP_STATUS" == "200" ]] || {
    echo "ERROR=render_tree_http_status:$HTTP_STATUS"
    exit 1
}

"$PYTHON" - "$BODY" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any


path = pathlib.Path(sys.argv[1])
payload = json.loads(path.read_text(encoding="utf-8"))

TARGET_TABLE = (
    "control.v3.feature_store_historical_corrections.recent_audits"
)

TARGET_BODY = (
    "control.v3.feature_store_historical_corrections.recent.body"
)

TARGET_ROW_PREFIX = (
    "control.v3.feature_store_historical_corrections.recent.row."
)


def children_of(node: Any) -> list[Any]:
    if not isinstance(node, dict):
        return []

    children = node.get("children") or []

    if not isinstance(children, list):
        return []

    return children


rows: list[tuple[str, dict[str, Any]]] = []


def visit(node: Any, path_value: str) -> None:
    if not isinstance(node, dict):
        return

    rows.append((path_value, node))

    for index, child in enumerate(children_of(node)):
        visit(
            child,
            f"{path_value}/children/{index}",
        )


root = payload.get("root")

if not isinstance(root, dict):
    raise SystemExit("ERROR=render_tree_root_missing")

visit(root, "root")

by_id: dict[str, list[tuple[str, dict[str, Any]]]] = {}

for node_path, node in rows:
    node_id = str(node.get("node_id") or "")

    if not node_id:
        continue

    by_id.setdefault(node_id, []).append(
        (node_path, node)
    )


table_matches = by_id.get(TARGET_TABLE, [])
body_matches = by_id.get(TARGET_BODY, [])

audit_rows = [
    (node_path, node)
    for node_path, node in rows
    if str(node.get("node_id") or "").startswith(
        TARGET_ROW_PREFIX
    )
    and str(node.get("type") or "") == "table_row"
]

audit_cells = [
    (node_path, node)
    for node_path, node in rows
    if str(node.get("node_id") or "").startswith(
        TARGET_ROW_PREFIX
    )
    and str(node.get("type") or "") == "table_cell"
]

print(f"total_node_count={len(rows)}")
print(f"recent_table_count={len(table_matches)}")
print(f"recent_body_count={len(body_matches)}")
print(f"recent_row_count={len(audit_rows)}")
print(f"recent_cell_count={len(audit_cells)}")

for node_path, node in table_matches:
    print(
        "RECENT_TABLE "
        f"path={node_path} "
        f"type={node.get('type')} "
        f"children={len(children_of(node))}"
    )

for node_path, node in body_matches:
    print(
        "RECENT_BODY "
        f"path={node_path} "
        f"type={node.get('type')} "
        f"children={len(children_of(node))}"
    )

for index, (node_path, node) in enumerate(
    audit_rows[:5],
    start=1,
):
    child_ids = [
        str(child.get("node_id") or "")
        for child in children_of(node)
        if isinstance(child, dict)
    ]

    print(
        f"RECENT_ROW index={index} "
        f"path={node_path} "
        f"id={node.get('node_id')} "
        f"cells={len(child_ids)} "
        f"child_ids={','.join(child_ids)}"
    )

if len(table_matches) != 1:
    raise SystemExit(
        "ERROR=recent_table_count:"
        + str(len(table_matches))
    )

if len(body_matches) != 1:
    raise SystemExit(
        "ERROR=recent_body_count:"
        + str(len(body_matches))
    )

if not audit_rows:
    raise SystemExit(
        "ERROR=recent_audit_rows_missing"
    )

if len(audit_cells) < len(audit_rows) * 4:
    raise SystemExit(
        "ERROR=recent_audit_cells_insufficient:"
        + str(len(audit_cells))
    )

print("recent_audit_structure=TABLE_BODY_ROWS_CELLS")
print("recent_audit_shape_contract=OK")
print(
    "VERDICT="
    "MARKETCORE_UI_HISTORICAL_CORRECTIONS_"
    "RECENT_AUDITS_SHAPE_V1_READY"
)
PY

echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
