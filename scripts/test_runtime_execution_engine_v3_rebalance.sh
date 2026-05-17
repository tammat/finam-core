#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_execution_engine.py

python - <<'PY'
import time

from finam_core.runtime.runtime_execution_engine import RuntimeExecutionEngine


class Provider:
    def load_symbols(self):
        return ["SBER@MISX"]


calls = []


def rebalance():
    calls.append("rebalance_called")


engine = RuntimeExecutionEngine(
    universe_provider=Provider(),
    rebalance_interval_sec=0.01,
    rebalance_callback=rebalance,
)

engine.supervisor_tick()

time.sleep(0.02)

engine.supervisor_tick()

assert len(calls) >= 1

print("OK: RuntimeExecutionEngine v3 rebalance callback")
PY
