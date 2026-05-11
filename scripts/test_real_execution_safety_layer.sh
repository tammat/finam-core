#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f src/finam_core/execution/real_execution_safety.py

PYTHONPATH=src \
EXECUTION_ENABLED=1 \
REAL_TRADING_ENABLED=1 \
REAL_STOCKS_ONLY=1 \
REAL_MAX_QTY=1 \
REAL_DUPLICATE_TTL_SEC=60 \
python - <<'PY'
from finam_core.execution.real_execution_safety import RealExecutionSafetyLayer

layer = RealExecutionSafetyLayer()

assert layer.check("SBER@MISX", "BUY", 1, execution_mode="real").allowed is True
assert layer.check("BRM6@RTSX", "BUY", 1, execution_mode="real").reason == "REAL_FUTURES_BLOCKED"
assert layer.check("SBER@MISX", "BUY", 2, execution_mode="real").reason == "REAL_QTY_LIMIT_EXCEEDED"
assert layer.check("SBER@MISX", "HOLD", 1, execution_mode="real").reason == "REAL_INVALID_SIDE"

dup_layer = RealExecutionSafetyLayer()
assert dup_layer.check("SBER@MISX", "BUY", 1, execution_mode="real").allowed is True
assert dup_layer.check("SBER@MISX", "BUY", 1, execution_mode="real").reason == "REAL_DUPLICATE_ORDER_BLOCKED"

print("REAL_EXECUTION_SAFETY_LAYER_RUNTIME_OK")
PY

python -m py_compile src/finam_core/execution/real_execution_safety.py

echo "REAL_EXECUTION_SAFETY_LAYER_TEST_OK"
