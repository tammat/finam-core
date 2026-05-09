#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export FUTURES_SPEC_BR_STEP_VALUE=10

python - <<'PY'
from finam_core.portfolio.portfolio_mtm_service import PortfolioMtmService

class FakeEquity:
    def calculate(self, *, equity):
        class E:
            used_margin = 50000.0
            free_margin = equity - 50000.0
            margin_utilization_pct = round(50000.0 / equity * 100, 2)
            positions_count = 2
        return E()

class Svc(PortfolioMtmService):
    def __init__(self):
        super().__init__(database_url="fake")
        self.equity_service = FakeEquity()

    def load_latest_positions(self):
        return [
            {"symbol": "BRM6", "qty": -2, "avg_price": 98.32},
            {"symbol": "SBERP", "qty": 100, "avg_price": 324.95},
        ]

    def load_last_price(self, symbol):
        return {"BRM6": 97.32, "SBERP": 330.0}.get(symbol)

s = Svc().calculate(base_equity=366337.96)

assert s.unrealized_pnl == 2505.0, s
assert s.live_equity == 368842.96, s
assert s.used_margin == 50000.0, s
assert s.positions_count == 2, s

print("PORTFOLIO_MTM_SERVICE_OK")
PY
