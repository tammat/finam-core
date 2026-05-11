#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

SAFETY="src/finam_core/execution/real_execution_safety.py"
CLIENT="src/finam_core/adapters/grpc/orders_client.py"

grep -q "broker_position_qty: float | None = None" "$SAFETY"
grep -q "local_position_qty: float | None = None" "$SAFETY"
grep -q "PositionMismatchGate().check" "$SAFETY"
! grep -q "BROKER_POSITION_QTY_" "$SAFETY"
! grep -q "LOCAL_POSITION_QTY_" "$SAFETY"

grep -q "position_qty_provider=None" "$CLIENT"
grep -q "set_position_qty_provider" "$CLIENT"
grep -q "_resolve_position_qty_pair" "$CLIENT"
grep -q "POSITION_QTY_PROVIDER_FAILED" "$CLIENT"
grep -q "broker_position_qty=broker_position_qty" "$CLIENT"
grep -q "local_position_qty=local_position_qty" "$CLIENT"

PYTHONPATH=src \
EXECUTION_ENABLED=1 \
REAL_TRADING_ENABLED=1 \
REAL_STOCKS_ONLY=1 \
POSITION_MISMATCH_HARD_BLOCK=1 \
python - <<'PY'
from finam_core.execution.real_execution_safety import RealExecutionSafetyLayer

allowed = RealExecutionSafetyLayer().check(
    "SBER@MISX",
    "BUY",
    1,
    execution_mode="real",
    broker_position_qty=1,
    local_position_qty=1,
)
assert allowed.allowed is True

blocked = RealExecutionSafetyLayer().check(
    "SBER@MISX",
    "BUY",
    1,
    execution_mode="real",
    broker_position_qty=1,
    local_position_qty=0,
)
assert blocked.allowed is False
assert blocked.reason == "POSITION_MISMATCH_BLOCK"

print("POSITION_MISMATCH_PROVIDER_RUNTIME_OK")
PY

python -m py_compile src/finam_core/execution/real_execution_safety.py
python -m py_compile src/finam_core/adapters/grpc/orders_client.py

echo "POSITION_MISMATCH_PROVIDER_BEFORE_REAL_ORDER_TEST_OK"
