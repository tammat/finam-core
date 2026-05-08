#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.simulation.signal_paper_trade_tracker import SignalPaperTradeTracker

tracker = SignalPaperTradeTracker()

t = tracker.open_trade(
    symbol="BRN6@RTSX",
    side="BUY",
    entry=80.0,
    stop_loss=79.0,
    take_profit=82.0,
    qty=1,
)

closed = tracker.on_price("BRN6@RTSX", 82.1)

assert len(closed) == 1, closed
assert closed[0].status == "CLOSED", closed[0]
assert closed[0].close_reason == "TAKE_PROFIT", closed[0]
assert closed[0].pnl == 2.0, closed[0]
assert closed[0].r_multiple == 2.0, closed[0]

summary = tracker.daily_summary()
assert summary["closed"] == 1, summary
assert summary["wins"] == 1, summary
assert summary["pnl"] == 2.0, summary

print("SIGNAL_PAPER_TRADE_TRACKER_OK")
PY
