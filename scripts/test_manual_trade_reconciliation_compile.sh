#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/reconciliation/manual_trade_reconciliation.py

python - <<'PY'
from finam_core.reconciliation.manual_trade_reconciliation import ManualTradeReconciliation

class FakeBroker:
    def get_positions(self):
        return [
            {
                "symbol": "BRM6@RTSX",
                "qty": "4",
                "average_price": {"value": "107.77"},
                "current_price": {"value": "108.10"},
                "unrealized_pnl": {"value": "1320.0"},
            }
        ]

r = ManualTradeReconciliation(FakeBroker())
positions = r.get_broker_positions()

assert len(positions) == 1
assert positions[0].symbol == "BRM6@RTSX"
assert positions[0].qty == 4.0
assert positions[0].average_price == 107.77

print("OK: manual trade reconciliation compile and fake broker test passed")
PY
