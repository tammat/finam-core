#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.position_order_tracker import PositionOrderTracker

tracker = PositionOrderTracker()

state = tracker.evaluate(
    "BRM6@RTSX",
    2,
    [
        {"symbol": "BRM6@RTSX", "type": "STOP", "side": "SELL", "qty": 2},
        {"symbol": "BRM6@RTSX", "type": "LIMIT", "side": "SELL", "qty": 1},
    ],
)

assert state.protected is True, state
assert state.stop_qty == 2.0, state
assert state.take_qty == 1.0, state
assert state.protection_gap_qty == 0.0, state

state = tracker.evaluate("NGK6@RTSX", 3, [])
assert state.protected is False, state
assert state.protection_gap_qty == 3.0, state

print("POSITION_ORDER_TRACKER_OK")
PY
