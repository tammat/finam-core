#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/trade_pnl_reconstructor.py

python - <<'PY'
from finam_core.analytics.trade_pnl_reconstructor import reconstruct_closed_trades

rows = [
    {"id": 1, "symbol": "BRM6@RTSX", "side": "BUY", "qty": 0.5, "price": 100.0, "commission": 1.0},
    {"id": 2, "symbol": "BRM6@RTSX", "side": "SELL", "qty": 0.5, "price": 110.0, "commission": 1.0},
]

closed = reconstruct_closed_trades(rows)

assert len(closed) == 1
assert closed[0].gross_pnl == 5.0
assert closed[0].commission == 2.0
assert closed[0].net_pnl == 3.0

print("TRADE_PNL_RECONSTRUCTOR_OK")
PY
