#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.order_state_machine import OrderState

o = OrderState(order_id="br_1", symbol="BRM6@RTSX", side="BUY", qty=3)

o.on_submitted()
o.on_accepted()

o.on_partial_fill(1, 100.0)
assert o.state == "PARTIAL_FILLED", o
assert o.filled_qty == 1.0, o
assert o.remaining_qty() == 2.0, o

o.on_partial_fill(2, 101.0)
assert o.state == "FILLED", o
assert o.filled_qty == 3.0, o
assert round(o.avg_fill_price, 6) == round((1 * 100.0 + 2 * 101.0) / 3, 6), o
assert o.remaining_qty() == 0.0, o

try:
    o.on_partial_fill(1, 102.0)
    raise AssertionError("overfill after FILLED was not blocked")
except ValueError as e:
    assert "cannot_fill_terminal_order_state" in str(e), e

o2 = OrderState(order_id="br_2", symbol="BRM6@RTSX", side="BUY", qty=3)
o2.on_submitted()
o2.on_accepted()

try:
    o2.on_partial_fill(4, 100.0)
    raise AssertionError("overfill was not blocked")
except ValueError as e:
    assert "overfill_detected" in str(e), e

print("ORDER_STATE_MACHINE_FILLS_OK")
PY
