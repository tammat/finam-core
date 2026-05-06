#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_RESTART_RECOVERY=1

python - <<'PY'
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline


class DummyPipeline:
    _run_restart_recovery_if_needed = PaperTradingPipeline._run_restart_recovery_if_needed
    _refresh_broker_position_hard_gate = PaperTradingPipeline._refresh_broker_position_hard_gate

    def __init__(self):
        self._restart_recovery_done = False
        self._broker_position_qty_by_symbol = {"BRM6@RTSX": 1.0}
        self._broker_orders_by_symbol = {"BRM6@RTSX": [{"order_id": "o1"}]}
        self._broker_position_halt_by_symbol = {}

    def _sync_broker_positions_readonly(self):
        self._broker_position_qty_by_symbol = {"BRM6@RTSX": 1.0}

    def _sync_broker_open_orders_if_needed(self):
        self._broker_orders_by_symbol = {"BRM6@RTSX": [{"order_id": "o1"}]}


p = DummyPipeline()

p._run_restart_recovery_if_needed()
assert p._restart_recovery_done is True, p.__dict__

# второй вызов не должен падать и не должен повторять recovery
p._run_restart_recovery_if_needed()
assert p._restart_recovery_done is True, p.__dict__

print("RESTART_RECOVERY_OK")
PY
