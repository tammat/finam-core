#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/signal_repository.py \
  src/finam_core/analytics/closed_trade_engine.py \
  src/finam_core/analytics/closed_trade_repository.py

python - <<'PY'
from finam_core.analytics.closed_trade_engine import ClosedTradeEngine, TradeFill

engine = ClosedTradeEngine()

entry = TradeFill(
    id=1,
    ts="2026-05-14T10:00:00+00:00",
    symbol="BRM6@RTSX",
    side="BUY",
    qty=1,
    price=100.0,
    commission=0.1,
    fill_id="synthetic-entry-fill",
    payload={
        "signal_id": "synthetic-signal-001",
        "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
        "horizon": "INTRADAY",
        "regime": "trend_high_vol",
        "timeframe": "M5",
        "origin": "synthetic_test",
    },
)

exit = TradeFill(
    id=2,
    ts="2026-05-14T10:05:00+00:00",
    symbol="BRM6@RTSX",
    side="SELL",
    qty=1,
    price=102.0,
    commission=0.1,
    fill_id="synthetic-exit-fill",
    payload={
        "origin": "synthetic_test",
    },
)

closed = engine.build_closed_trades([entry, exit])

assert len(closed) == 1
t = closed[0]

assert t.symbol == "BRM6@RTSX"
assert t.signal_id == "synthetic-signal-001"
assert t.strategy == "BR_CONSERVATIVE_BREAKOUT_M5"
assert t.horizon == "INTRADAY"
assert t.regime == "trend_high_vol"
assert round(t.net_pnl, 4) == 1.8
assert t.payload["entry_payload"]["origin"] == "synthetic_test"

print("OK: synthetic signal -> fill -> closed_trade metadata chain")
PY
