#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.pnl_reconstruction import (
    TradeFill,
    reconstruct_closed_trades_fifo,
)

fills = [
    TradeFill(symbol="BRM6@RTSX", side="buy", price=100.0, qty=2.0, commission=1.0),
    TradeFill(symbol="BRM6@RTSX", side="buy", price=110.0, qty=1.0, commission=0.5),
    TradeFill(symbol="BRM6@RTSX", side="sell", price=120.0, qty=2.5, commission=1.25),
]

closed = reconstruct_closed_trades_fifo("BRM6@RTSX", fills)

assert len(closed) == 2

assert closed[0].gross_pnl == 40.0
assert closed[0].commission == 2.0
assert closed[0].pnl == 38.0

assert closed[1].gross_pnl == 5.0
assert closed[1].commission == 0.5
assert closed[1].pnl == 4.5

assert round(sum(t.gross_pnl for t in closed), 4) == 45.0
assert round(sum(t.commission for t in closed), 4) == 2.5
assert round(sum(t.pnl for t in closed), 4) == 42.5

fallback = reconstruct_closed_trades_fifo(
    "SBER@MISX",
    [
        TradeFill(symbol="SBER@MISX", side="buy", price=100.0, qty=1.0),
        TradeFill(symbol="SBER@MISX", side="sell", price=110.0, qty=1.0),
    ],
    fallback_commission_rate=0.001,
)

assert len(fallback) == 1
assert fallback[0].gross_pnl == 10.0
assert round(fallback[0].commission, 4) == 0.21
assert round(fallback[0].pnl, 4) == 9.79

print("TEST_PNL_RECONSTRUCTION_OK")
PY
