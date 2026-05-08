#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.auto_breakeven_manager import AutoBreakevenManager, BreakevenRule

m = AutoBreakevenManager([
    BreakevenRule(symbol="BRM6", entry_price=98.32),
    BreakevenRule(symbol="NGK6", entry_price=2.841),
])

a1 = m.on_take_profit_fill("BRM6", tp_index=1)
assert a1 is not None
assert a1.symbol == "BRM6"
assert a1.new_stop == 98.32

a2 = m.on_take_profit_fill("BRM6", tp_index=1)
assert a2 is None

a3 = m.on_take_profit_fill("NGK6", tp_index=2)
assert a3 is None

print("AUTO_BREAKEVEN_MANAGER_OK")
PY
