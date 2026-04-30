#!/usr/bin/env bash
set -euo pipefail

cat > /tmp/finam_portfolio_snapshot.json <<'JSON'
{
  "cash": 152062.36,
  "starting_cash": 387875.83,
  "realized_pnl": 0.0,
  "daily_realized_pnl": 0.0,
  "peak_equity": 387875.83,
  "positions": {
    "BRM6@RTSX": {
      "qty": 1.0,
      "avg_price": 110.5,
      "mark_price": 111.0,
      "realized_pnl": 0.0
    }
  }
}
JSON

PYTHONPATH=src python - <<'PY'
from finam_core.accounting.position_manager import PositionManager
from finam_core.accounting.portfolio_bootstrap import load_portfolio_snapshot, bootstrap_position_manager

pm = PositionManager(starting_cash=0)
snap = load_portfolio_snapshot("/tmp/finam_portfolio_snapshot.json")
bootstrap_position_manager(pm, snap)

assert round(pm.cash, 2) == 152062.36
assert round(pm.starting_cash, 2) == 387875.83
assert "BRM6@RTSX" in pm.positions
assert pm.positions["BRM6@RTSX"].qty == 1.0

print("OK portfolio_bootstrap")
PY
