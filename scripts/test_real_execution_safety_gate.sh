#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real_dry_run
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1
export ENABLE_REAL_EXECUTION_SAFETY_GATE=1
export REAL_EXECUTION_SYMBOL_ALLOWLIST=BRM6@RTSX
export REAL_EXECUTION_MAX_QTY=1

python - <<'PY'
from finam_core.execution.real_execution import RealExecutionEngine

class DummyOrdersClient:
    def place_market_order(self, *args, **kwargs):
        raise RuntimeError("REAL ORDER MUST NOT BE CALLED")

engine = RealExecutionEngine(orders_client=DummyOrdersClient())

ok = engine.execute({"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1.0, "price": 102.15}, {"last": 102.15})
assert ok.status == "DRY_RUN_ACCEPTED", ok

bad_symbol = engine.execute({"symbol": "SBERP@MISX", "side": "BUY", "qty": 1.0, "price": 320.0}, {"last": 320.0})
assert bad_symbol.status == "REJECTED", bad_symbol
assert "symbol_not_in_allowlist" in bad_symbol.reason, bad_symbol

bad_qty = engine.execute({"symbol": "BRM6@RTSX", "side": "BUY", "qty": 2.0, "price": 102.15}, {"last": 102.15})
assert bad_qty.status == "REJECTED", bad_qty
assert "qty_exceeds_max" in bad_qty.reason, bad_qty

print("REAL_EXECUTION_SAFETY_GATE_OK")
PY
