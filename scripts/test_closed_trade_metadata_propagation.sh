#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/closed_trade_engine.py \
  src/finam_core/analytics/closed_trade_repository.py

python - <<'PY'
from finam_core.analytics.closed_trade_engine import ClosedTradeEngine, TradeFill

engine = ClosedTradeEngine()

closed = engine.build_closed_trades([
    TradeFill(
        id=1,
        ts="2026-05-14T10:00:00Z",
        symbol="BRM6@RTSX",
        side="BUY",
        qty=1,
        price=100.0,
        commission=0.1,
        fill_id="entry-fill",
        payload={
            "signal_id": "sig-001",
            "strategy": "BR_CONSERVATIVE_BREAKOUT_M5",
            "horizon": "INTRADAY",
            "regime": "trend_high_vol",
        },
    ),
    TradeFill(
        id=2,
        ts="2026-05-14T10:05:00Z",
        symbol="BRM6@RTSX",
        side="SELL",
        qty=1,
        price=101.0,
        commission=0.1,
        fill_id="exit-fill",
        payload={},
    ),
])

assert len(closed) == 1
trade = closed[0]

assert trade.signal_id == "sig-001", trade
assert trade.strategy == "BR_CONSERVATIVE_BREAKOUT_M5", trade
assert trade.horizon == "INTRADAY", trade
assert trade.regime == "trend_high_vol", trade
assert trade.net_pnl == 0.8, trade

print("OK: closed trade metadata propagation")
PY

python - <<'PY'
from pathlib import Path

repo = Path("src/finam_core/analytics/closed_trade_repository.py").read_text(encoding="utf-8")

assert "signal_id, symbol, side" in repo
assert "horizon, strategy, regime" in repo
assert "t.signal_id" in repo
assert "t.strategy" in repo
assert "t.regime" in repo

print("OK: closed trade repository metadata insert")
PY
