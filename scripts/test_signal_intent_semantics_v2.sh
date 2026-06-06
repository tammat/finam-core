#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/finam_core/signals/intent_semantics_v2.py

python3 - <<'PY'
from finam_core.signals.intent_semantics_v2 import (
    IntentAction,
    classify_intent_semantics_v2,
)

cases = [
    ("BUY", 0, 1, IntentAction.OPEN_LONG, 1, False, True),
    ("BUY", 2, 1, IntentAction.ADD_LONG, 3, False, False),
    ("SELL", 2, 1, IntentAction.REDUCE_LONG, 1, True, False),
    ("SELL", 1, 1, IntentAction.CLOSE_LONG, 0, True, False),
    ("SELL", 0, 1, IntentAction.OPEN_SHORT, -1, False, True),
    ("SELL", -2, 1, IntentAction.ADD_SHORT, -3, False, False),
    ("BUY", -2, 1, IntentAction.REDUCE_SHORT, -1, True, False),
    ("BUY", -1, 1, IntentAction.CLOSE_SHORT, 0, True, False),
]

for side, pos, qty, action, result, reduce_only, opens in cases:
    d = classify_intent_semantics_v2(
        side=side,
        current_position=pos,
        requested_qty=qty,
    )
    print(
        "INTENT_SEMANTICS_ROW "
        f"side={side} pos={pos} qty={qty} "
        f"action={d.action.value} result={d.resulting_position} "
        f"reduce_only={int(d.reduce_only)} opens={int(d.opens_position)}"
    )
    assert d.action == action
    assert d.resulting_position == result
    assert d.reduce_only is reduce_only
    assert d.opens_position is opens

cross = classify_intent_semantics_v2(side="SELL", current_position=1, requested_qty=2)
assert cross.action == IntentAction.CLOSE_LONG
assert cross.crosses_zero is True
assert cross.resulting_position == -1

noop = classify_intent_semantics_v2(side="WAIT", current_position=1, requested_qty=1)
assert noop.action == IntentAction.NOOP

print("SIGNAL_INTENT_SEMANTICS_V2_OK")
PY
