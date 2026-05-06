#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.trailing_order_manager import TrailingOrderManager

m = TrailingOrderManager(trail_abs=0.40, min_replace_step=0.10)

d = m.evaluate_long(symbol="BRM6@RTSX", qty=3, last_price=111.60, current_stop=None)
assert d.action == "PLACE_STOP", d
assert d.side == "SELL", d
assert d.stop_price == 111.20, d

d = m.evaluate_long(symbol="BRM6@RTSX", qty=3, last_price=111.65, current_stop=111.20)
assert d.action == "HOLD", d
assert d.reason == "replace_step_too_small", d

d = m.evaluate_long(symbol="BRM6@RTSX", qty=3, last_price=111.80, current_stop=111.20)
assert d.action == "REPLACE_STOP", d
assert d.stop_price == 111.40, d

d = m.evaluate_long(symbol="BRM6@RTSX", qty=0, last_price=111.80, current_stop=111.20)
assert d.action == "HOLD", d
assert d.reason == "no_long_position", d

print("TRAILING_ORDER_MANAGER_OK")
PY
