#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/profit_lock_engine.py

python - <<'PY'
from finam_core.execution.profit_lock_engine import ProfitLockEngine

e = ProfitLockEngine()

# qty=1: partial close запрещён, только stop.
d = e.evaluate_long(qty=1, entry_price=100, current_price=110, stop_price=95)
assert d.action == "MOVE_STOP"
assert d.qty_to_close == 0.0
assert d.new_stop == 103.75

# qty>1: можно частично закрыть.
d = e.evaluate_long(qty=4, entry_price=100, current_price=110, stop_price=95)
assert d.action == "PARTIAL_CLOSE_AND_MOVE_STOP"
assert d.qty_to_close == 2.0
assert d.new_stop == 102.5

# +1R: breakeven.
d = e.evaluate_long(qty=1, entry_price=100, current_price=105, stop_price=95)
assert d.action == "MOVE_STOP"
assert d.new_stop == 100

print("OK: ProfitLockEngine")
PY
