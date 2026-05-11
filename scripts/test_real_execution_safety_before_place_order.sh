#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

FILE="src/finam_core/adapters/grpc/orders_client.py"

grep -q "RealExecutionSafetyLayer" "$FILE"
grep -q "_assert_real_execution_safety" "$FILE"
grep -q "REAL_EXECUTION_SAFETY_BLOCK" "$FILE"

PYTHONPATH=src python - <<'PY'
from pathlib import Path

p = Path("src/finam_core/adapters/grpc/orders_client.py")
lines = p.read_text(encoding="utf-8").splitlines()

place_order_lines = [
    i for i, line in enumerate(lines)
    if ".PlaceOrder(" in line
]

assert place_order_lines, "NO_PLACE_ORDER_CALLS_FOUND"

for idx in place_order_lines:
    before = "\n".join(lines[max(0, idx - 8):idx])
    assert "_assert_real_execution_safety" in before, (
        f"PlaceOrder at line {idx + 1} has no safety-check before it"
    )

print("REAL_EXECUTION_SAFETY_BEFORE_PLACE_ORDER_RUNTIME_OK")
PY

python -m py_compile src/finam_core/execution/real_execution_safety.py
python -m py_compile src/finam_core/adapters/grpc/orders_client.py

echo "REAL_EXECUTION_SAFETY_BEFORE_PLACE_ORDER_TEST_OK"
