#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/closed_trade_engine.py \
  src/scripts/analytics/build_closed_trades.py

python - <<'PY'
from datetime import datetime, timezone, timedelta

from finam_core.analytics.closed_trade_engine import Fill, build_closed_trades_fifo

t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

fills = [
    Fill("SBER@MISX", "BUY", 10, 100.0, 1.0, "test", "M5", t0),
    Fill("SBER@MISX", "SELL", 10, 105.0, 1.0, "test", "M5", t0 + timedelta(minutes=5)),
]

closed = build_closed_trades_fifo(fills)

assert len(closed) == 1
assert closed[0].gross_pnl == 50.0
assert closed[0].commission == 2.0
assert closed[0].net_pnl == 48.0
assert closed[0].holding_seconds == 300

print("CLOSED_TRADES_ENGINE_UNIT_OK")
PY

echo "CLOSED_TRADES_INTEGRATION_V1_TEST_OK"
