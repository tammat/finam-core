#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/engine/restart_recovery_coordinator.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
import os

from finam_core.engine.restart_recovery_coordinator import RestartRecoveryCoordinator


class MockCoordinator:
    def __init__(self):
        self.called = False

    def reconcile(self, broker_positions=None, broker_orders=None, context=None):
        self.called = True
        assert broker_positions == [{"symbol": "BRM6@RTSX", "qty": 4.0}]
        assert broker_orders == [{"symbol": "BRM6@RTSX", "orders": []}]
        assert context == {"source": "restart_recovery"}

        class Result:
            reconciliation_processed = True
            errors = []

        return Result()


class MockPipeline:
    def __init__(self):
        self._restart_recovery_done = False
        self._broker_position_qty_by_symbol = {}
        self._broker_orders_by_symbol = {}
        self._broker_position_halt_by_symbol = {}
        self.engine_coordinator = MockCoordinator()

    def _sync_broker_positions_readonly(self):
        self._broker_position_qty_by_symbol = {"BRM6@RTSX": 4.0}

    def _sync_broker_open_orders_if_needed(self):
        self._broker_orders_by_symbol = {"BRM6@RTSX": []}

    def _refresh_broker_position_hard_gate(self):
        self._broker_position_halt_by_symbol = {}


for key in (
    "ENABLE_RESTART_RECOVERY",
    "ENABLE_ENGINE_COORDINATOR",
    "ENABLE_ENGINE_COORDINATOR_RECONCILE",
):
    os.environ.pop(key, None)

pipeline = MockPipeline()
result = RestartRecoveryCoordinator(pipeline).run_if_needed()

assert result.event == "RESTART_RECOVERY_DISABLED", result
assert result.executed is False, result
assert pipeline._restart_recovery_done is True

pipeline = MockPipeline()
os.environ["ENABLE_RESTART_RECOVERY"] = "1"
os.environ["ENABLE_ENGINE_COORDINATOR"] = "1"

result = RestartRecoveryCoordinator(pipeline).run_if_needed()

assert result.event == "RESTART_RECOVERY_DONE", result
assert result.executed is True, result
assert result.positions == 1, result
assert result.open_order_symbols == 1, result
assert result.halted_symbols == 0, result
assert result.error is None, result
assert pipeline._restart_recovery_done is True
assert pipeline.engine_coordinator.called is True

print("OK: restart recovery coordinator")
PY

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "from finam_core.engine.restart_recovery_coordinator import RestartRecoveryCoordinator" in text
assert "self.restart_recovery_coordinator = RestartRecoveryCoordinator(self)" in text
assert "coordinator.run_if_needed()" in text

print("OK: paper_pipeline uses RestartRecoveryCoordinator")
PY
