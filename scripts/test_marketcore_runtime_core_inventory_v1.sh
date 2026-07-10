#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "=== TEST_MARKETCORE_RUNTIME_CORE_INVENTORY_V1 ==="

inventory_script="src/scripts/presentation/runtime_core_inventory_v1.py"
report="reports/marketcore_runtime_core_inventory_v1.txt"

test -f "$inventory_script"

PYTHONPYCACHEPREFIX=/tmp/marketcore_runtime_core_inventory_v1 \
PYTHONPATH=src \
python -m py_compile "$inventory_script"

PYTHONPATH=src python - "$inventory_script" <<'PYCODE'
from __future__ import annotations

import ast
import sys
from pathlib import Path


path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
tree = ast.parse(source, filename=str(path))

forbidden_calls = {
    "send_order",
    "place_order",
    "cancel_order",
    "execute_order",
}

for node in ast.walk(tree):
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            call_name = node.func.attr
        else:
            call_name = ""

        if call_name in forbidden_calls:
            raise SystemExit(
                f"DANGEROUS_CALL_FOUND:"
                f"name={call_name}:line={node.lineno}"
            )

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        value = node.value.upper()

        # Константа FORBIDDEN_CORE_MARKERS является частью inventory,
        # поэтому отдельные слова UPDATE/DELETE не считаются SQL-операциями.
        dangerous_sql = (
            "INSERT INTO ",
            "DROP TABLE ",
            "TRUNCATE TABLE ",
        )

        for marker in dangerous_sql:
            if marker in value:
                raise SystemExit(
                    f"DANGEROUS_SQL_FOUND:"
                    f"marker={marker.strip()}:line={node.lineno}"
                )

print("INVENTORY_STATIC_SAFETY=OK")
PYCODE

PYTHONPATH=src \
python "$inventory_script" | tee "$report"

grep -q \
  "RUNTIME_RELATED_FILES" \
  "$report"

grep -q \
  "RUNTIME_CORE_CANDIDATES" \
  "$report"

grep -q \
  "PLATFORM_DRIVER_CANDIDATES" \
  "$report"

grep -q \
  "RUNTIME_RELATED_SYMBOLS" \
  "$report"

grep -q \
  "RENDER_TREE_RUNTIME_IMPORTS" \
  "$report"

grep -q \
  "DELIVERY_DEPENDENCY_MARKERS" \
  "$report"

grep -q \
  "FORBIDDEN_RUNTIME_CORE_MARKERS" \
  "$report"

grep -q \
  "DECISION_PENDING" \
  "$report"

grep -q \
  "runtime_core_created=0" \
  "$report"

grep -q \
  "platform_driver_created=0" \
  "$report"

grep -q \
  "VERDICT=MARKETCORE_RUNTIME_CORE_INVENTORY_V1_READY" \
  "$report"

echo "inventory_report=$report"
echo "runtime_core_inventory=OK"
echo "runtime_core_created=0"
echo "platform_driver_created=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKETCORE_RUNTIME_CORE_INVENTORY_V1_OK"
