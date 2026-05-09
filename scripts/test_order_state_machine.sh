#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.oms.order_state_machine import OrderStateMachine

fsm = OrderStateMachine()

assert fsm.can_transition("CREATED", "SENT") is True
assert fsm.can_transition("SENT", "ACCEPTED") is True
assert fsm.can_transition("ACCEPTED", "PARTIALLY_FILLED") is True
assert fsm.can_transition("PARTIALLY_FILLED", "FILLED") is True
assert fsm.can_transition("ACCEPTED", "CANCEL_REQUESTED") is True
assert fsm.can_transition("CANCEL_REQUESTED", "CANCELLED") is True

assert fsm.can_transition("FILLED", "CANCELLED") is False
assert fsm.can_transition("CANCELLED", "SENT") is False
assert fsm.can_transition("REJECTED", "SENT") is False

ok = fsm.validate_transition("CREATED", "SENT")
bad = fsm.validate_transition("FILLED", "CANCELLED")

assert ok.allowed is True
assert ok.reason == "allowed"

assert bad.allowed is False
assert bad.reason == "invalid_transition:FILLED->CANCELLED"

assert fsm.is_terminal("FILLED") is True
assert fsm.is_terminal("CANCELLED") is True
assert fsm.is_terminal("ACCEPTED") is False

print("ORDER_STATE_MACHINE_OK")
PY
