#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/finam_core/signals/position_action.py

python3 - <<'PY'
from finam_core.signals.position_action import classify_position_action, PositionAction

cases = [
    ("BUY", 0, 1, PositionAction.OPEN_LONG, 1),
    ("BUY", 2, 1, PositionAction.ADD_LONG, 3),
    ("SELL", 2, 1, PositionAction.REDUCE_LONG, 1),
    ("SELL", 1, 1, PositionAction.CLOSE_LONG, 0),
    ("SELL", 0, 1, PositionAction.OPEN_SHORT, -1),
    ("SELL", -2, 1, PositionAction.ADD_SHORT, -3),
    ("BUY", -2, 1, PositionAction.REDUCE_SHORT, -1),
    ("BUY", -1, 1, PositionAction.CLOSE_SHORT, 0),
]

for side, pos, qty, expected_action, expected_result in cases:
    decision = classify_position_action(
        side=side,
        current_position=pos,
        quantity=qty,
    )
    print(
        "POSITION_ACTION_ROW "
        f"side={side} pos={pos} qty={qty} "
        f"action={decision.action.value} result={decision.resulting_position}"
    )
    assert decision.action == expected_action
    assert decision.resulting_position == expected_result

cross = classify_position_action(side="SELL", current_position=1, quantity=2)
assert cross.action == PositionAction.CLOSE_LONG
assert cross.crosses_zero is True
assert cross.resulting_position == -1

noop = classify_position_action(side="WAIT", current_position=1, quantity=1)
assert noop.action == PositionAction.NOOP

print("SIGNAL_INTENT_POSITION_ACTION_V1_OK")
PY
