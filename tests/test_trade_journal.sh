#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python - <<'PY'
from finam_core.analytics.trade_journal import TradeJournal, TradeRow

rows = [
    TradeRow("BR", "BUY", 1, 100.0, 0.01),
    TradeRow("BR", "SELL", 1, 101.0, 0.01),
    TradeRow("BR", "SELL", 1, 105.0, 0.01),
    TradeRow("BR", "BUY", 1, 104.0, 0.01),
]

s = TradeJournal().summarize(rows)

assert s.trades_count == 4
assert s.closed_cycles == 2
assert s.wins == 2
assert round(s.total_pnl, 4) == 1.96
assert round(s.winrate, 4) == 1.0

print("OK trade_journal")
PY
