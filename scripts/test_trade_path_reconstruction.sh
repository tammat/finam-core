#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.trade_path_reconstruction import (
    TradePathInput,
    reconstruct_trade_path,
)

long_win = reconstruct_trade_path(
    TradePathInput(
        trade_index=1,
        symbol="BRM6@RTSX",
        side="long",
        entry_price=100.0,
        exit_price=110.0,
        qty=1.0,
        pnl=10.0,
    )
)

assert long_win.reconstructed_mfe > 10.0
assert long_win.reconstructed_mae < 0.0
assert 0.0 < long_win.exit_efficiency < 1.0

long_loss = reconstruct_trade_path(
    TradePathInput(
        trade_index=2,
        symbol="BRM6@RTSX",
        side="long",
        entry_price=100.0,
        exit_price=95.0,
        qty=1.0,
        pnl=-5.0,
    )
)

assert long_loss.reconstructed_mfe > 0.0
assert long_loss.reconstructed_mae < 0.0
assert long_loss.exit_efficiency < 0.0

short_win = reconstruct_trade_path(
    TradePathInput(
        trade_index=3,
        symbol="BRM6@RTSX",
        side="short",
        entry_price=100.0,
        exit_price=90.0,
        qty=1.0,
        pnl=10.0,
    )
)

assert short_win.reconstructed_mfe > 10.0
assert short_win.reconstructed_mae < 0.0
assert 0.0 < short_win.exit_efficiency < 1.0

print("TEST_TRADE_PATH_RECONSTRUCTION_OK")
PY
