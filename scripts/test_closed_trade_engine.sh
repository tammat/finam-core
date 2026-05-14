#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/closed_trade_engine.py

python - <<'PY'
from finam_core.analytics.closed_trade_engine import (
    ClosedTradeEngine,
    TradeFill,
    summarize_closed_trades,
)

fills = [
    TradeFill(id=1, ts="2026-05-14 10:00", symbol="BRM6", side="BUY", qty=1, price=100.0, commission=1.0),
    TradeFill(id=2, ts="2026-05-14 10:10", symbol="BRM6", side="SELL", qty=1, price=103.0, commission=1.0),
    TradeFill(id=3, ts="2026-05-14 10:20", symbol="BRM6", side="BUY", qty=1, price=105.0, commission=1.0),
    TradeFill(id=4, ts="2026-05-14 10:30", symbol="BRM6", side="SELL", qty=1, price=104.0, commission=1.0),
]

engine = ClosedTradeEngine()
closed = engine.build_closed_trades(fills)

assert len(closed) == 2

assert closed[0].side == "LONG"
assert closed[0].gross_pnl == 3.0
assert closed[0].commission == 2.0
assert closed[0].net_pnl == 1.0

assert closed[1].gross_pnl == -1.0
assert closed[1].net_pnl == -3.0

summary = summarize_closed_trades(closed)

assert summary["trades"] == 2
assert summary["wins"] == 1
assert summary["losses"] == 1
assert round(summary["winrate"], 2) == 50.00
assert summary["net_pnl"] == -2.0
assert summary["expectancy"] == -1.0

print("OK: closed trade engine works")
print(summary)
PY
