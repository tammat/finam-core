#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

FILE="src/finam_core/execution/real_execution_safety.py"

grep -q "REAL_ALLOWED_SYMBOLS" "$FILE"
grep -q "REAL_SYMBOL_NOT_ALLOWED" "$FILE"

PYTHONPATH=src \
EXECUTION_ENABLED=1 \
REAL_TRADING_ENABLED=1 \
REAL_STOCKS_ONLY=1 \
REAL_ALLOWED_SYMBOLS=SBER@MISX \
POSITION_MISMATCH_HARD_BLOCK=0 \
python - <<'PY'
from finam_core.execution.real_execution_safety import RealExecutionSafetyLayer

ok = RealExecutionSafetyLayer().check("SBER@MISX", "BUY", 1, execution_mode="real")
assert ok.allowed is True, ok

blocked = RealExecutionSafetyLayer().check("GAZP@MISX", "BUY", 1, execution_mode="real")
assert blocked.allowed is False
assert blocked.reason == "REAL_SYMBOL_NOT_ALLOWED"

fut = RealExecutionSafetyLayer().check("BRM6@RTSX", "BUY", 1, execution_mode="real")
assert fut.allowed is False
assert fut.reason == "REAL_FUTURES_BLOCKED"

print("REAL_ALLOWED_SYMBOLS_GATE_RUNTIME_OK")
PY

python -m py_compile src/finam_core/execution/real_execution_safety.py

echo "REAL_ALLOWED_SYMBOLS_GATE_TEST_OK"
