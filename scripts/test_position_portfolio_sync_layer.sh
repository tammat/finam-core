#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/portfolio/position_portfolio_sync.py \
  src/finam_core/accounting/position_manager.py

python - <<'PY'
from dataclasses import dataclass

from finam_core.accounting.position_manager import PositionManager
from finam_core.portfolio.position_portfolio_sync import (
    AuthoritativePosition,
    PositionPortfolioSyncLayer,
)


@dataclass
class Fill:
    symbol: str
    side: str
    qty: float
    price: float
    commission: float = 0.0
    fill_id: str | None = None


pm = PositionManager(starting_cash=100000.0)

pm.apply_fill(Fill(symbol="SBER@MISX", side="BUY", qty=2, price=300, fill_id="f1"))

cash_before = pm.cash
realized_before = pm.realized_pnl

sync = PositionPortfolioSyncLayer(position_manager=pm)

event = sync.sync_position(
    AuthoritativePosition(
        symbol="SBER@MISX",
        qty=1,
        avg_price=300,
        reason="test_repair",
    )
)

assert event["event"] == "POSITION_PORTFOLIO_SYNC", event
assert event["position_event"]["event"] == "AUTHORITATIVE_POSITION_SYNC", event
assert pm.positions["SBER@MISX"].qty == 1.0
assert pm.cash == cash_before
assert pm.realized_pnl == realized_before

event = sync.sync_position(
    AuthoritativePosition(
        symbol="SBER@MISX",
        qty=0,
        reason="broker_flat",
    )
)

assert pm.positions["SBER@MISX"].qty == 0.0
assert pm.positions["SBER@MISX"].avg_price == 0.0
assert pm.cash == cash_before
assert pm.realized_pnl == realized_before

print("OK: position/portfolio sync layer does not affect cash or realized pnl")
PY
