#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/real_buy_execution_adapter.py \
  src/scripts/run_real_buy_execution_adapter.py

python - <<'PY'
from finam_core.execution.real_buy_execution_adapter import RealBuyExecutionAdapter

a = RealBuyExecutionAdapter()

ok = a.validate(
    symbol="SBER@MISX",
    side="BUY",
    qty=10,
    max_qty=100,
    max_position_value=30000,
    planned_price=300,
    kill_switch=False,
)
assert ok.allowed is True

sell = a.validate(
    symbol="SBER@MISX",
    side="SELL",
    qty=10,
    max_qty=100,
    max_position_value=30000,
    planned_price=300,
    kill_switch=False,
)
assert sell.allowed is False

futures = a.validate(
    symbol="BRM6@RTSX",
    side="BUY",
    qty=1,
    max_qty=100,
    max_position_value=30000,
    planned_price=110,
    kill_switch=False,
)
assert futures.allowed is False

ks = a.validate(
    symbol="SBER@MISX",
    side="BUY",
    qty=10,
    max_qty=100,
    max_position_value=30000,
    planned_price=300,
    kill_switch=True,
)
assert ks.allowed is False

print("OK: real buy execution adapter")
PY
