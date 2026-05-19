#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/real_sell_execution_adapter.py \
  src/scripts/run_real_sell_execution_adapter.py

python - <<'PY'
from finam_core.execution.real_sell_execution_adapter import RealSellExecutionAdapter

a = RealSellExecutionAdapter()

ok = a.validate(
    symbol="SBER@MISX",
    side="SELL",
    qty=1,
    available_qty=1,
    max_qty=1,
    planned_price=326.5,
    kill_switch=False,
)
assert ok.allowed is True

no_position = a.validate(
    symbol="SBER@MISX",
    side="SELL",
    qty=1,
    available_qty=0,
    max_qty=1,
    planned_price=326.5,
    kill_switch=False,
)
assert no_position.allowed is False

wrong_symbol = a.validate(
    symbol="LKOH@MISX",
    side="SELL",
    qty=1,
    available_qty=1,
    max_qty=1,
    planned_price=5200,
    kill_switch=False,
)
assert wrong_symbol.allowed is False

print("OK: real sell execution adapter")
PY
