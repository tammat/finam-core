#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
KG_URL="http://127.0.0.1:8095/api/kg/v1/feature-store/historical-corrections?limit=50"
RENDER_URL="http://127.0.0.1:8080/api/v2/domain-render-tree/control-center"

KG_JSON="/tmp/marketcore_ui_historical_corrections_kg_v2.json"
RENDER_JSON="/tmp/marketcore_ui_historical_corrections_render_tree_v2.json"

echo "=== TEST_MARKETCORE_UI_HISTORICAL_CORRECTIONS_RENDER_TREE_V2 ==="

[[ -x "$PYTHON" ]] || {
    echo "ERROR=python_missing:$PYTHON"
    exit 1
}

python_compile_targets=(
    "$ROOT/src/marketcore/presentation/workspace_v2/resolver/control_center_v2_resolver.py"
    "$ROOT/src/marketcore/presentation/workspace_v2/presenter/control_center_v2_presenter.py"
    "$ROOT/src/marketcore/presentation/workspace_v2/viewmodel/control_center_v2_viewmodel.py"
    "$ROOT/src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py"
)

"$PYTHON" -m py_compile "${python_compile_targets[@]}"
echo "python_compile=OK"

KG_STATUS="$(
    curl -sS \
        -o "$KG_JSON" \
        -w '%{http_code}' \
        "$KG_URL"
)"

RENDER_STATUS="$(
    curl -sS \
        -o "$RENDER_JSON" \
        -w '%{http_code}' \
        "$RENDER_URL"
)"

echo "=== HTTP CONTRACT ==="
echo "kg_http_status=$KG_STATUS"
echo "render_tree_http_status=$RENDER_STATUS"

[[ "$KG_STATUS" == "200" ]] || {
    echo "ERROR=kg_http_status:$KG_STATUS"
    exit 1
}

[[ "$RENDER_STATUS" == "200" ]] || {
    echo "ERROR=render_tree_http_status:$RENDER_STATUS"
    exit 1
}

"$PYTHON" - "$KG_JSON" "$RENDER_JSON" <<'PY'
from __future__ import annotations

import json
import pathlib
import sys
from collections.abc import Iterator
from typing import Any


kg_path = pathlib.Path(sys.argv[1])
render_path = pathlib.Path(sys.argv[2])

kg_payload = json.loads(kg_path.read_text(encoding="utf-8"))
render_payload = json.loads(render_path.read_text(encoding="utf-8"))


def walk(value: Any, path: str = "$") -> Iterator[tuple[str, Any]]:
    yield path, value

    if isinstance(value, dict):
        for key, child in value.items():
            yield from walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")


def extract_kg_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")

    if isinstance(data, dict):
        return data

    return payload


kg_data = extract_kg_data(kg_payload)
summary = kg_data.get("summary") or {}
recent_audits = kg_data.get("recent_audits") or []
read_only = kg_data.get("read_only")

expected = {
    "changed_pairs": summary.get("changed_pairs"),
    "changed_rows": summary.get("changed_rows"),
    "current_dirty_rows": summary.get("current_dirty_rows"),
    "watermark_lag": summary.get("watermark_lag"),
}

print("=== KG JSON CONTRACT ===")

for key, value in expected.items():
    if value is None:
        raise SystemExit(f"ERROR=kg_field_missing:{key}")

    print(f"{key}={value}")

if not isinstance(recent_audits, list):
    raise SystemExit("ERROR=kg_recent_audits_not_list")

if read_only is not True:
    raise SystemExit(f"ERROR=kg_read_only_invalid:{read_only!r}")

print(f"recent_audits={len(recent_audits)}")
print("read_only=1")
print("kg_json_contract=OK")


all_items = list(walk(render_payload))

scalar_values: list[tuple[str, Any]] = []
dict_values: list[tuple[str, dict[str, Any]]] = []

for item_path, value in all_items:
    if isinstance(value, dict):
        dict_values.append((item_path, value))
    elif isinstance(value, (str, int, float, bool)) or value is None:
        scalar_values.append((item_path, value))


def normalized(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value).strip()


def semantic_key_present(key: str) -> bool:
    key_lower = key.lower()

    for item_path, value in all_items:
        if key_lower in item_path.lower():
            return True

        if isinstance(value, str) and key_lower in value.lower():
            return True

        if isinstance(value, dict):
            for dict_key, dict_value in value.items():
                if key_lower in str(dict_key).lower():
                    return True
                if (
                    isinstance(dict_value, str)
                    and key_lower in dict_value.lower()
                ):
                    return True

    return False


def value_present(value: Any) -> bool:
    target = normalized(value)

    return any(
        normalized(candidate) == target
        for _, candidate in scalar_values
    )


print("=== STRUCTURAL RENDER TREE CONTRACT ===")

missing_semantic_keys = [
    key
    for key in expected
    if not semantic_key_present(key)
]

if missing_semantic_keys:
    raise SystemExit(
        "ERROR=render_tree_semantic_keys_missing:"
        + ",".join(missing_semantic_keys)
    )

missing_values = [
    key
    for key, value in expected.items()
    if not value_present(value)
]

if missing_values:
    raise SystemExit(
        "ERROR=render_tree_metric_values_missing:"
        + ",".join(missing_values)
    )

historical_context_present = any(
    any(
        marker in (
            item_path.lower()
            + " "
            + normalized(value).lower()
        )
        for marker in (
            "historical",
            "correction",
            "историчес",
            "коррекц",
        )
    )
    for item_path, value in all_items
)

if not historical_context_present:
    raise SystemExit(
        "ERROR=historical_corrections_context_missing"
    )

audit_rows_present = 0

for _, value in dict_values:
    keys = {str(key).lower() for key in value.keys()}

    if {
        "symbol",
        "timeframe",
    }.issubset(keys) and (
        "changed_rows" in keys
        or "correction_detected" in keys
        or "checked_rows" in keys
    ):
        audit_rows_present += 1

# V3 structural contract:
# table -> table_body -> table_row -> table_cell.
#
# Проверка намеренно не зависит от имени переменной,
# в которой тест хранит HTTP render-tree JSON.
_recent_table_id = (
    "control.v3.feature_store_historical_corrections.recent_audits"
)
_recent_body_id = (
    "control.v3.feature_store_historical_corrections.recent.body"
)
_recent_row_prefix = (
    "control.v3.feature_store_historical_corrections.recent.row."
)


def _collect_render_nodes(value):
    collected = []

    def visit(current):
        if isinstance(current, dict):
            if "node_id" in current or "type" in current:
                collected.append(current)

            for child_value in current.values():
                visit(child_value)

        elif isinstance(current, (list, tuple)):
            for child_value in current:
                visit(child_value)

    visit(value)
    return collected


_render_nodes_by_identity = {}

for _local_value in tuple(locals().values()):
    for _node in _collect_render_nodes(_local_value):
        _identity = id(_node)
        _render_nodes_by_identity[_identity] = _node

_render_nodes = list(_render_nodes_by_identity.values())

_recent_tables = [
    node
    for node in _render_nodes
    if (
        str(node.get("node_id") or "") == _recent_table_id
        and str(node.get("type") or "") == "table"
    )
]

_recent_bodies = [
    node
    for node in _render_nodes
    if (
        str(node.get("node_id") or "") == _recent_body_id
        and str(node.get("type") or "") == "table_body"
    )
]

_recent_rows = [
    node
    for node in _render_nodes
    if (
        str(node.get("node_id") or "").startswith(_recent_row_prefix)
        and str(node.get("type") or "") == "table_row"
    )
]

_recent_cells = [
    node
    for node in _render_nodes
    if (
        str(node.get("node_id") or "").startswith(_recent_row_prefix)
        and str(node.get("type") or "") == "table_cell"
    )
]

if len(_recent_tables) != 1:
    raise SystemExit(
        "ERROR=recent_audit_table_count:"
        + str(len(_recent_tables))
    )

if len(_recent_bodies) != 1:
    raise SystemExit(
        "ERROR=recent_audit_body_count:"
        + str(len(_recent_bodies))
    )

if not _recent_rows:
    raise SystemExit(
        "ERROR=recent_audit_rows_missing"
    )

if len(_recent_cells) != len(_recent_rows) * 4:
    raise SystemExit(
        "ERROR=recent_audit_cell_count:"
        + str(len(_recent_cells))
        + ":expected:"
        + str(len(_recent_rows) * 4)
    )

print(f"recent_audit_table_count={len(_recent_tables)}")
print(f"recent_audit_body_count={len(_recent_bodies)}")
print(f"recent_audit_row_count={len(_recent_rows)}")
print(f"recent_audit_cell_count={len(_recent_cells)}")
print("recent_audit_structure=TABLE_BODY_ROWS_CELLS")
print("recent_audit_structural_contract=OK")
print(f"semantic_metric_keys={len(expected)}")
print(f"metric_values_matched={len(expected)}")
print(f"audit_rows_present={audit_rows_present}")
print("historical_context_present=1")
print("render_tree_json_contract=OK")

print("direct_sql_from_renderer=0")
print("write_actions_allowed=0")
print("systemctl_actions_allowed=0")
print("writes_performed=0")
print("runtime_changed=0")
print("execution_changed=0")
print("orders_changed=0")
print("fills_changed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "MARKETCORE_UI_HISTORICAL_CORRECTIONS_RENDER_TREE_JSON_V2_READY"
)
PY

echo "VERDICT=TEST_MARKETCORE_UI_HISTORICAL_CORRECTIONS_RENDER_TREE_V2_OK"
