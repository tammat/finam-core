#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/runtime_execution_engine.py

python - <<'PY'
from finam_core.runtime.runtime_execution_engine import RuntimeExecutionEngine


class Provider:
    def load_symbols(self):
        return ["SBER@MISX"]


class DeadWorker:
    def poll(self):
        return 0


calls = []


def runner(symbol):
    calls.append(symbol)
    return DeadWorker()


engine = RuntimeExecutionEngine(
    universe_provider=Provider(),
    worker_runner=runner,
)

engine.supervisor_tick()
assert "SBER@MISX" in engine.workers

engine.supervisor_tick()
assert engine.worker_states["SBER@MISX"].status in ("running", "exited")
assert calls.count("SBER@MISX") >= 2

print("OK: RuntimeExecutionEngine v3 reaps exited workers")
PY
