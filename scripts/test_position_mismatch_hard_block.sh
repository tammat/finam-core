#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f src/finam_core/reconciliation/position_mismatch_gate.py

grep -q "POSITION_MISMATCH_BLOCK" src/finam_core/reconciliation/position_mismatch_gate.py
grep -q "POSITION_MATCH_OK" src/finam_core/reconciliation/position_mismatch_gate.py
grep -q "POSITION_MISMATCH_HARD_BLOCK" src/finam_core/execution/real_execution_safety.py
grep -q "BROKER_POSITION_QTY_" src/finam_core/execution/real_execution_safety.py
grep -q "LOCAL_POSITION_QTY_" src/finam_core/execution/real_execution_safety.py

PYTHONPATH=src python - <<'PY'
from finam_core.reconciliation.position_mismatch_gate import PositionMismatchGate

gate = PositionMismatchGate(tolerance=0.000001)

assert gate.check("SBER@MISX", 1, 1).allowed is True
assert gate.check("SBER@MISX", 1, 0).allowed is False
assert gate.check("SBER@MISX", 1, 0).reason == "POSITION_MISMATCH_BLOCK"

print("POSITION_MISMATCH_GATE_RUNTIME_OK")
PY

PYTHONPATH=src \
EXECUTION_ENABLED=1 \
REAL_TRADING_ENABLED=1 \
REAL_STOCKS_ONLY=1 \
POSITION_MISMATCH_HARD_BLOCK=1 \
BROKER_POSITION_QTY_SBER_MISX=1 \
LOCAL_POSITION_QTY_SBER_MISX=0 \
python - <<'PY'
from finam_core.execution.real_execution_safety import RealExecutionSafetyLayer

decision = RealExecutionSafetyLayer().check("SBER@MISX", "BUY", 1, execution_mode="real")
assert decision.allowed is False
assert decision.reason == "POSITION_MISMATCH_BLOCK"

print("POSITION_MISMATCH_SAFETY_LAYER_RUNTIME_OK")
PY

python -m py_compile src/finam_core/reconciliation/position_mismatch_gate.py
python -m py_compile src/finam_core/execution/real_execution_safety.py

echo "POSITION_MISMATCH_HARD_BLOCK_TEST_OK"
