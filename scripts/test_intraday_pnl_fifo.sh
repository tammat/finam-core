#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python -m py_compile src/scripts/analytics/build_intraday_pnl.py

PYTHONPATH=src python - <<'PY'
from scripts.analytics.build_intraday_pnl import PositionState, calculate_trade_pnl

s = PositionState()

pnl = []
pnl.append(calculate_trade_pnl(s, "BUY", 0.5, 107.05))
pnl.append(calculate_trade_pnl(s, "SELL", 0.5, 106.11))
pnl.append(calculate_trade_pnl(s, "SELL", 0.5, 106.11))
pnl.append(calculate_trade_pnl(s, "BUY", 0.5, 102.72))

assert round(sum(pnl), 6) == 1.225000, pnl
assert s.qty == 0.0, s

print("INTRADAY_PNL_FIFO_UNIT_OK")
PY

echo "INTRADAY_PNL_FIFO_TEST_OK"
