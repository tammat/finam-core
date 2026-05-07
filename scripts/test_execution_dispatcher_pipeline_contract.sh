#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
import os
from finam_core.execution.execution_dispatcher import ExecutionDispatcher


class FakeRealExecution:
    def __init__(self):
        self.called = False

    def execute(self, intent, market_state=None):
        self.called = True
        return {"status": "REAL_EXECUTION_CALLED", "intent": intent}


real = FakeRealExecution()

dispatcher = ExecutionDispatcher(
    orders_client=None,
    real_execution_engine=real,
)

os.environ["EXECUTION_MODE"] = "real_dry_run"

result = dispatcher.execute(
    intent={"symbol": "SBER@MISX", "side": "BUY", "qty": 1, "price": 300},
    market_state={"last": 300},
)

assert result["status"] == "REAL_EXECUTION_CALLED", result
assert real.called is True

print("OK: ExecutionDispatcher pipeline contract")
PY
