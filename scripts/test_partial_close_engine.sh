#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/partial_close_engine.py

python - <<'PY'
from finam_core.execution.partial_close_engine import PartialCloseEngine

e = PartialCloseEngine()

# qty=1: partial close невозможен.
d = e.evaluate_long(qty=1, entry_price=100, current_price=110, stop_price=95)
assert d.action == "HOLD"
assert d.reason == "single_qty_no_partial"

# qty=4, +1R: TP1 закрывает 25%, минимум 1.
d = e.evaluate_long(qty=4, entry_price=100, current_price=105, stop_price=95)
assert d.action == "PARTIAL_CLOSE"
assert d.stage == "TP1"
assert d.qty_to_close == 1.0
assert d.remaining_qty == 3.0

# qty=4, +2R: TP2 закрывает 50%.
d = e.evaluate_long(qty=4, entry_price=100, current_price=110, stop_price=95, tp1_done=True)
assert d.action == "PARTIAL_CLOSE"
assert d.stage == "TP2"
assert d.qty_to_close == 2.0
assert d.remaining_qty == 2.0

# TP1 уже выполнен, +1R повторно не закрываем.
d = e.evaluate_long(qty=4, entry_price=100, current_price=105, stop_price=95, tp1_done=True)
assert d.action == "HOLD"

print("OK: PartialCloseEngine")
PY
