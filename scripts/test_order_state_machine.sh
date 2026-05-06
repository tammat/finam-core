#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.order_state_machine import OrderState

o = OrderState(order_id="test_1", symbol="BRM6@RTSX", side="BUY", qty=3)

assert o.state == "NEW"

o.on_submitted()
assert o.state == "SUBMITTED"

o.on_accepted()
assert o.state == "ACCEPTED"

o.on_partial_fill(1, 64.10)
assert o.state == "PARTIAL_FILLED"
assert o.filled_qty == 1

o.on_partial_fill(2, 64.30)
assert o.state == "FILLED"
assert o.filled_qty == 3

print("ORDER_STATE_MACHINE_OK")
PY
