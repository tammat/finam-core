#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.trade_statistics import ClosedTrade, calculate_trade_statistics

trades = [
    ClosedTrade(symbol="BRM6@RTSX", side="buy", entry_price=100.0, exit_price=105.0, qty=1.0, pnl=5.0),
    ClosedTrade(symbol="BRM6@RTSX", side="buy", entry_price=105.0, exit_price=103.0, qty=1.0, pnl=-2.0),
    ClosedTrade(symbol="BRM6@RTSX", side="sell", entry_price=103.0, exit_price=99.0, qty=1.0, pnl=4.0),
    ClosedTrade(symbol="SBER@MISX", side="buy", entry_price=300.0, exit_price=301.0, qty=1.0, pnl=1.0),
]

stats = calculate_trade_statistics("BRM6@RTSX", trades)

assert stats.symbol == "BRM6@RTSX"
assert stats.trades == 3
assert stats.wins == 2
assert stats.losses == 1
assert stats.net_pnl == 7.0
assert stats.gross_profit == 9.0
assert stats.gross_loss == 2.0
assert stats.profit_factor == 4.5
assert stats.max_drawdown == -2.0

print("TEST_ANALYTICS_TRADE_STATISTICS_OK")
PY
