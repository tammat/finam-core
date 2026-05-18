#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/signal_lifecycle_engine.py \
  src/scripts/analyze_watch_candidates_runtime.py

python - <<'PY'
from finam_core.runtime.signal_lifecycle_engine import SignalLifecycleEngine

e = SignalLifecycleEngine()

assert e.evaluate(
    state="NEW",
    current_price=101,
    entry_price=100,
    stop_loss=95,
    take_profit=110,
).state == "TRIGGERED"

assert e.evaluate(
    state="TRIGGERED",
    current_price=94,
    entry_price=100,
    stop_loss=95,
    take_profit=110,
).close_reason == "STOP_LOSS"

assert e.evaluate(
    state="TRIGGERED",
    current_price=111,
    entry_price=100,
    stop_loss=95,
    take_profit=110,
).close_reason == "TAKE_PROFIT"

print("OK: signal lifecycle engine")
PY
