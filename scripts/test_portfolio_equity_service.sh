#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.portfolio.portfolio_equity_service import PortfolioEquityService

class FakeMargin:
    def calculate(self, *, symbol, qty):
        class M:
            required_initial_margin = 0.0

        m = M()
        if symbol == "BRM6":
            m.required_initial_margin = 50000.0
        elif symbol == "NGK6":
            m.required_initial_margin = 24000.0
        return m

class Service(PortfolioEquityService):
    def load_latest_positions(self):
        return [
            {"symbol": "BRM6", "qty": -2},
            {"symbol": "NGK6", "qty": 3},
            {"symbol": "SBERP", "qty": 100},
        ]

svc = Service(database_url="fake", margin_calculator=FakeMargin())
s = svc.calculate(equity=366337.96)

assert s.positions_count == 3, s
assert s.used_margin == 74000.0, s
assert s.free_margin == 292337.96, s
assert s.margin_utilization_pct == 20.2, s

print("PORTFOLIO_EQUITY_SERVICE_OK")
PY
