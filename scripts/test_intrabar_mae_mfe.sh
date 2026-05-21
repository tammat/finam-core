#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from datetime import datetime

from finam_core.analytics.intrabar_mae_mfe import (
    MarketBar,
    TradeWindow,
    reconstruct_intrabar_quality,
)

trade = TradeWindow(
    trade_index=1,
    symbol="BRM6@RTSX",
    side="long",
    entry_time=datetime(2026, 1, 1, 10, 0),
    exit_time=datetime(2026, 1, 1, 10, 15),
    entry_price=100.0,
    exit_price=106.0,
    qty=1.0,
    pnl=6.0,
)

bars = [
    MarketBar(symbol="BRM6@RTSX", ts=datetime(2026, 1, 1, 10, 0), high=103.0, low=99.0, close=102.0),
    MarketBar(symbol="BRM6@RTSX", ts=datetime(2026, 1, 1, 10, 5), high=110.0, low=101.0, close=108.0),
    MarketBar(symbol="BRM6@RTSX", ts=datetime(2026, 1, 1, 10, 15), high=107.0, low=104.0, close=106.0),
]

quality = reconstruct_intrabar_quality([trade], bars)

assert len(quality) == 1
assert quality[0].mfe == 10.0
assert quality[0].mae == -1.0
assert quality[0].max_favorable_price == 110.0
assert quality[0].max_adverse_price == 99.0
assert quality[0].exit_efficiency == 0.6

print("TEST_INTRABAR_MAE_MFE_OK")
PY
