#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_state.py \
  src/finam_core/runtime/runtime_telemetry.py \
  src/finam_core/runtime/runtime_execution_engine.py

python - <<'PY'
from finam_core.runtime.runtime_execution_engine import RuntimeExecutionEngine


class Provider:
    def __init__(self):
        self.symbols = ["SBER@MISX", "GAZP@MISX"]

    def get_symbols(self):
        return self.symbols


engine = RuntimeExecutionEngine(
    universe_provider=Provider(),
    supervisor_interval_sec=0.01,
    rebalance_interval_sec=0.01,
)

engine.supervisor_tick()

assert "SBER@MISX" in engine.workers
assert "GAZP@MISX" in engine.workers

engine.universe_provider.symbols = ["SBER@MISX"]
engine.supervisor_tick()

assert "SBER@MISX" in engine.workers
assert "GAZP@MISX" not in engine.workers
assert engine.worker_states["GAZP@MISX"].status == "stopped"

engine.stop_all_workers(reason="test_shutdown")

assert engine.worker_states["SBER@MISX"].status == "stopped"

print("OK: RuntimeExecutionEngine v3 supervisor lifecycle")
PY
