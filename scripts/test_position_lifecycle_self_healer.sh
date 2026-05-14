#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/position_lifecycle_self_healer.py

python - <<'PY'
from finam_core.execution.position_lifecycle_self_healer import PositionLifecycleSelfHealer

h = PositionLifecycleSelfHealer()

d = h.evaluate(state_exists=False, actual_qty=0, trailing_active=False, current_stop=None)
assert d.action == "NOOP"

d = h.evaluate(state_exists=True, actual_qty=0, trailing_active=True, current_stop=100)
assert d.action == "DELETE_ORPHAN_STATE"
assert d.should_delete_state is True

d = h.evaluate(state_exists=True, actual_qty=1, trailing_active=True, current_stop=None)
assert d.action == "MARK_STALE_TRAILING"
assert d.should_clear_trailing_cache is True

d = h.evaluate(state_exists=True, actual_qty=1, trailing_active=True, current_stop=100)
assert d.action == "OK"

print("OK: position lifecycle self healer")
PY
