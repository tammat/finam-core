#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_capital_allocator.py \
  src/scripts/run_runtime_capital_allocator.py

python - <<'PY'
from finam_core.runtime.runtime_capital_allocator import RuntimeCapitalAllocator

a = RuntimeCapitalAllocator()

ok = a.allocate(
    equity=100000,
    cash=50000,
    margin_utilization_pct=10,
    drawdown=0,
    signal_score=3,
    risk_reward=2,
    correlation_pressure=0,
    runtime_severity="INFO",
)
assert ok.allowed is True
assert ok.max_position_value > 0

blocked = a.allocate(
    equity=100000,
    cash=50000,
    margin_utilization_pct=80,
    drawdown=0,
    signal_score=3,
    risk_reward=2,
    correlation_pressure=0,
    runtime_severity="INFO",
)
assert blocked.allowed is False

critical = a.allocate(
    equity=100000,
    cash=50000,
    margin_utilization_pct=10,
    drawdown=0,
    signal_score=3,
    risk_reward=2,
    correlation_pressure=0,
    runtime_severity="CRITICAL",
)
assert critical.allowed is False

print("OK: runtime capital allocator")
PY
