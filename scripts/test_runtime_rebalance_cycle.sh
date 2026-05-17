#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_rebalance_cycle.py \
  src/finam_core/runtime/runtime_execution_engine.py \
  src/finam_core/runtime/runtime_universe_allocator.py

python - <<'PY'
from finam_core.runtime.runtime_execution_engine import RuntimeExecutionEngine
from finam_core.runtime.runtime_rebalance_cycle import RuntimeRebalanceCycle


class Provider:
    def load_symbols(self):
        return ["SBER@MISX"]


class Allocator:
    def __init__(self):
        self.calls = 0

    def allocate(self, *, max_symbols, min_score):
        self.calls += 1
        assert max_symbols == 3
        assert min_score == 0.5
        return 2


allocator = Allocator()
cycle = RuntimeRebalanceCycle(
    allocator,
    max_symbols=3,
    min_score=0.5,
)

engine = RuntimeExecutionEngine(
    universe_provider=Provider(),
    rebalance_interval_sec=0.0,
    rebalance_callback=cycle,
)

engine.supervisor_tick()
engine.supervisor_tick()

assert allocator.calls >= 1
assert cycle.last_active_count == 2
assert cycle.last_error is None

print("OK: RuntimeRebalanceCycle integrated with RuntimeExecutionEngine v3")
PY
