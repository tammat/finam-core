#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from datetime import datetime, timezone, timedelta

from finam_core.analytics.closed_trade_reconstruction_v2 import (
    TradeFillV2,
    reconstruct_closed_trades_v2,
)

t0 = datetime.now(timezone.utc)

fills = [
    TradeFillV2(
        trade_id=1,
        ts=t0,
        symbol="BRM6@RTSX",
        side="BUY",
        qty=1,
        price=100,
        strategy="test",
        timeframe="M5",
        trade_source="paper",
        origin="paper",
        fill_id="f1",
    ),
    TradeFillV2(
        trade_id=2,
        ts=t0 + timedelta(minutes=5),
        symbol="BRM6@RTSX",
        side="SELL",
        qty=1,
        price=101,
        strategy="test",
        timeframe="M5",
        trade_source="paper",
        origin="paper",
        fill_id="f2",
    ),
]

closed = reconstruct_closed_trades_v2(fills)

assert len(closed) == 1
assert closed[0].side == "LONG"
assert closed[0].pnl == 1
assert closed[0].attribution_status == "MATCHED_FIFO"

print("TEST_CLOSED_TRADE_RECONSTRUCTION_V2_OK")
PY

python -m py_compile \
  src/finam_core/analytics/closed_trade_reconstruction_v2.py \
  src/finam_core/analytics/closed_trade_reconstruction_v2_repository.py \
  src/scripts/build_closed_trade_reconstruction_v2.py
