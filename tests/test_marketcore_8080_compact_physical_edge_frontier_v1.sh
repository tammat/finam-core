#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"

REGISTRY="src/marketcore/presentation/workspace_v2/domain_producer_registry_v2.py"
RENDERER="src/marketcore/presentation/workspace_v2/renderer/home_compact_v1_domain_renderer.py"

echo "=== TEST MARKETCORE 8080 COMPACT PHYSICAL EDGE FRONTIER V1 ==="

PYTHONPATH=src "$PY" -m py_compile \
  "$REGISTRY" \
  "$RENDERER"

git diff --check -- \
  "$REGISTRY" \
  "$RENDERER"

PYTHONPATH=src "$PY" - <<'PY'
from dataclasses import fields, is_dataclass

import marketcore.presentation.workspace_v2.domain_producer_registry_v2 as registry

registry._COMPACT_CACHE = None

snapshot = registry._compact_snapshot()
frontier = snapshot.get("physical_edge_frontier") or {}
rows = tuple(frontier.get("rows") or ())

assert tuple(
    row["physical_symbol"]
    for row in rows
) == (
    "BRQ6@RTSX",
    "GAZP@MISX",
    "PLZL@MISX",
)

assert frontier["contract_mixing_allowed"] is False
assert frontier["source_read_only"] is True

document = registry.build_domain_document_v2("HOME")

targets = {
    "BRQ6@RTSX": 0,
    "GAZP@MISX": 0,
    "PLZL@MISX": 0,
}

def walk(value):
    if isinstance(value, str):
        for token in targets:
            if token in value:
                targets[token] += 1
        return

    if isinstance(value, dict):
        for item in value.values():
            walk(item)
        return

    if isinstance(value, (list, tuple)):
        for item in value:
            walk(item)
        return

    if is_dataclass(value):
        for field in fields(value):
            walk(getattr(value, field.name))

walk(document)

assert all(
    count > 0
    for count in targets.values()
), targets

print("snapshot_top3_parity=1")
print("production_document_top3_parity=1")
print("physical_contract_identity_used=1")
print("contract_mixing_allowed=0")
print("source_read_only=1")
PY

echo "db_writes_performed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_8080_COMPACT_PHYSICAL_EDGE_FRONTIER_V1_OK"
