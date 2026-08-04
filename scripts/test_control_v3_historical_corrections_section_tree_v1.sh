#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"

RENDERER="$ROOT/src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py"

echo "=== TEST CONTROL V3 HISTORICAL CORRECTIONS SECTION TREE V1 ==="

[[ -f "$RENDERER" ]] || {
    echo "ERROR=renderer_missing:$RENDERER"
    exit 1
}

"$PYTHON" -m py_compile "$RENDERER"

PYTHONPATH="$ROOT/src" "$PYTHON" - <<'PY'
from __future__ import annotations

from collections import Counter
from typing import Any

from marketcore.presentation.workspace_v2.renderer.control_compact_v3_domain_renderer import (
    _historical_corrections_section_v1,
)


TARGET_ID = "control.v3.feature_store_historical_corrections"

snapshot = {
    "historical_corrections": {
        "status": "READY",
        "read_only": True,
        "summary": {
            "changed_pairs": 17,
            "changed_rows": 32,
            "current_dirty_rows": 0,
            "watermark_lag": 0,
        },
        "recent_audits": [
            {
                "symbol": "TEST",
                "timeframe": "M5",
                "changed_rows": 1,
                "created_at": "2026-08-04T00:00:00+00:00",
            }
        ],
    }
}


def read_attr(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def children_of(obj: Any) -> tuple[Any, ...]:
    return tuple(read_attr(obj, "children", ()) or ())


def node_id_of(obj: Any) -> str:
    return str(read_attr(obj, "node_id", "") or "")


section = _historical_corrections_section_v1(snapshot)

rows: list[tuple[str, str]] = []


def visit(node: Any, path: str) -> None:
    node_id = node_id_of(node)

    if node_id:
        rows.append((path, node_id))

    for index, child in enumerate(children_of(node)):
        visit(child, f"{path}/children/{index}")


visit(section, "section")

counts = Counter(node_id for _, node_id in rows)

duplicates = {
    node_id: count
    for node_id, count in counts.items()
    if count > 1
}

target_count = counts.get(TARGET_ID, 0)

required_ids = {
    TARGET_ID,
    f"{TARGET_ID}.title",
    f"{TARGET_ID}.subtitle",
    f"{TARGET_ID}.metrics",
    f"{TARGET_ID}.changed_pairs",
    f"{TARGET_ID}.changed_rows",
    f"{TARGET_ID}.current_dirty_rows",
    f"{TARGET_ID}.watermark_lag",
    f"{TARGET_ID}.recent_audits",
}

missing_ids = sorted(required_ids - set(counts))

print(f"section_node_id_count={len(rows)}")
print(f"section_unique_node_id_count={len(counts)}")
print(f"duplicate_node_id_count={len(duplicates)}")
print(f"target_node_count={target_count}")
print(f"required_node_id_count={len(required_ids)}")

if duplicates:
    raise SystemExit(
        "ERROR=section_duplicate_node_ids:"
        + ",".join(sorted(duplicates))
    )

if target_count != 1:
    raise SystemExit(
        f"ERROR=target_node_count:{target_count}"
    )

if missing_ids:
    raise SystemExit(
        "ERROR=required_node_ids_missing:"
        + ",".join(missing_ids)
    )

print("section_tree_uniqueness=OK")
print("section_semantic_contract=OK")
PY

echo "writes_performed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_CONTROL_V3_HISTORICAL_CORRECTIONS_SECTION_TREE_V1_OK"
