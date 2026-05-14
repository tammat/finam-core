#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/reconciliation/manual_position_pnl_analyzer.py

python - <<'PY'
from finam_core.reconciliation.manual_position_pnl_analyzer import analyze_position

p = analyze_position(
    symbol="T",
    qty=50,
    average_price=324.25,
    current_price=318.52,
)

assert p is not None
assert p.symbol == "T"
assert p.status == "LOSS"
assert round(p.pnl_pct, 2) == -1.77

p2 = analyze_position(
    symbol="SGZH",
    qty=10000,
    average_price=0.8795,
    current_price=0.897,
)

assert p2 is not None
assert p2.status == "PROFIT"
assert round(p2.pnl_pct, 2) == 1.99

assert analyze_position(symbol="X", qty=1, average_price=None, current_price=10) is None
assert analyze_position(symbol="X", qty=1, average_price=0, current_price=10) is None

print("OK: manual position PnL analyzer works")
PY
