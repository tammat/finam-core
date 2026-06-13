#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile src/finam_core/analytics/closed_trade_engine.py

python3 - <<'PY'
from datetime import datetime, timezone
from finam_core.analytics.closed_trade_engine import Fill, build_closed_trades_fifo

fills = [
    Fill("BRN6@RTSX", "SELL", 1.0, 100.0, 0.0, "test", "M5", datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)),
    Fill("BRN6@RTSX", "BUY", 1.0, 95.0, 0.0, "test", "M5", datetime(2026, 6, 1, 10, 5, tzinfo=timezone.utc)),
]

closed = build_closed_trades_fifo(fills)

assert len(closed) == 1
assert closed[0].side == "SHORT"
assert closed[0].gross_pnl == 5.0
assert closed[0].net_pnl == 5.0

fills2 = [
    Fill("BRN6@RTSX", "BUY", 1.0, 100.0, 0.0, "test", "M5", datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)),
    Fill("BRN6@RTSX", "SELL", 1.0, 105.0, 0.0, "test", "M5", datetime(2026, 6, 1, 10, 5, tzinfo=timezone.utc)),
]

closed2 = build_closed_trades_fifo(fills2)

assert len(closed2) == 1
assert closed2[0].side == "LONG"
assert closed2[0].gross_pnl == 5.0
assert closed2[0].net_pnl == 5.0

print("CLOSED_TRADE_SHORT_SIDE_FIX_OK")
PY

echo "TEST_CLOSED_TRADE_MATERIALIZER_SHORT_SIDE_FIX_V1_OK"
