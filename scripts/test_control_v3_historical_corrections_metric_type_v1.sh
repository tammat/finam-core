#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

RENDERER="$ROOT/src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py"

echo "=== TEST CONTROL V3 HISTORICAL CORRECTIONS METRIC TYPE V3 ==="

[[ -f "$RENDERER" ]] || {
    echo "ERROR=renderer_missing:$RENDERER"
    exit 1
}

"$PYTHON" -m py_compile "$RENDERER"

"$PYTHON" - "$RENDERER" <<'PY'
from __future__ import annotations

import ast
import pathlib
import sys


path = pathlib.Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(path))

HELPER_NAME = "_historical_corrections_section_v1"

SECTION_NODE_ID = (
    "control.v3.feature_store_historical_corrections"
)

SEMANTIC_KEYS = {
    "changed_pairs",
    "changed_rows",
    "current_dirty_rows",
    "watermark_lag",
    "recent_audits",
}

FORBIDDEN_MARKERS = (
    "psycopg2",
    "DATABASE_URL",
    "systemctl",
    "subprocess",
)


def string_value(node: ast.AST | None) -> str | None:
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
    ):
        return node.value

    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []

        for value in node.values:
            if (
                isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                parts.append(value.value)

        return "".join(parts) if parts else None

    return None


def call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        return node.func.attr

    return None


helpers = [
    node
    for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name == HELPER_NAME
]

if len(helpers) != 1:
    raise SystemExit(
        f"ERROR=historical_helper_count:{len(helpers)}"
    )

helper = helpers[0]
lines = source.splitlines(keepends=True)

helper_source = "".join(
    lines[helper.lineno - 1:helper.end_lineno]
)

invalid_metric_count = helper_source.count(
    "RenderNodeTypeV2.METRIC"
)

if invalid_metric_count:
    raise SystemExit(
        "ERROR=invalid_render_node_type_metric:"
        + str(invalid_metric_count)
    )

for marker in FORBIDDEN_MARKERS:
    count = helper_source.count(marker)
    print(f"forbidden_marker={marker} count={count}")

    if count:
        raise SystemExit(
            f"ERROR=forbidden_marker_present:{marker}"
        )


# Все строковые константы внутри активного helper.
string_constants = {
    node.value
    for node in ast.walk(helper)
    if (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
    )
}


# Извлекаем node_id как из позиционных, так и из именованных аргументов.
node_ids: set[str] = set()
render_call_count = 0

for node in ast.walk(helper):
    if not isinstance(node, ast.Call):
        continue

    name = call_name(node)

    if name not in {
        "RenderNodeV2",
        "_leaf",
        "_metric",
        "_metric_row",
        "_value",
    }:
        continue

    render_call_count += 1

    # Распространённая сигнатура:
    # RenderNodeV2(node_type, node_id, ...)
    if len(node.args) >= 2:
        value = string_value(node.args[1])

        if value:
            node_ids.add(value)

    # Именованный node_id=...
    for keyword in node.keywords:
        if keyword.arg not in {
            "node_id",
            "id",
            "key",
            "metric_key",
        }:
            continue

        value = string_value(keyword.value)

        if value:
            node_ids.add(value)


section_found = (
    SECTION_NODE_ID in node_ids
    or SECTION_NODE_ID in string_constants
)

if not section_found:
    raise SystemExit(
        "ERROR=historical_section_node_id_missing:"
        + SECTION_NODE_ID
    )


# Семантические ключи могут быть самостоятельными node_id,
# суффиксами node_id либо message/value keys.
found_semantic_keys: set[str] = set()

for key in SEMANTIC_KEYS:
    if key in string_constants:
        found_semantic_keys.add(key)
        continue

    if any(
        node_id == key
        or node_id.endswith("." + key)
        or node_id.endswith("_" + key)
        for node_id in node_ids
    ):
        found_semantic_keys.add(key)


missing_semantic_keys = sorted(
    SEMANTIC_KEYS - found_semantic_keys
)

if missing_semantic_keys:
    raise SystemExit(
        "ERROR=semantic_keys_missing:"
        + ",".join(missing_semantic_keys)
    )


text_node_count = helper_source.count(
    "RenderNodeTypeV2.TEXT"
)

print(f"helper={HELPER_NAME}")
print(f"invalid_metric_type_count={invalid_metric_count}")
print(f"render_call_count={render_call_count}")
print(f"discovered_node_ids={len(node_ids)}")
print(f"string_constants={len(string_constants)}")
print(f"text_node_count={text_node_count}")
print(f"section_node_id={SECTION_NODE_ID}")
print(
    "semantic_keys="
    + ",".join(sorted(found_semantic_keys))
)
print(f"semantic_metric_count={len(found_semantic_keys)}")
print("node_id_detection=POSITIONAL_AND_KEYWORD_AST")
print("node_type_contract=VALID")
print("semantic_contract=OK")
print("source_contract=OK")
PY

echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CONTROL_V3_HISTORICAL_CORRECTIONS_METRIC_TYPE_V3_OK"
