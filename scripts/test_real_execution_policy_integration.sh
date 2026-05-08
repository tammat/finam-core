#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export REAL_TRADING_ENABLED=0

python - <<'PY'
from finam_core.execution.real_execution_engine import RealExecutionEngine


class DummyBroker:
    def submit_order(self, signal):
        return {"success": True}


class Signal:
    def __init__(self, symbol):
        self.symbol = symbol


engine = RealExecutionEngine(broker=DummyBroker())

r1 = engine.execute(Signal("SBER@MISX"))
assert r1["success"] is False
assert r1["status"] == "blocked_by_policy"

print("REAL_EXECUTION_POLICY_BLOCK_OK")
PY
