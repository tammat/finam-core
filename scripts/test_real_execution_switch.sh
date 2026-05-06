#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
import os
from finam_core.execution.real_execution import RealExecutionEngine


class DummyOrdersClient:
    def place_market_order(self, symbol, side, qty, price=None):
        return {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "status": "ACCEPTED",
        }


# dry-run должен блокировать реальную отправку
os.environ["REAL_EXECUTION_ENABLED"] = "0"
os.environ["REAL_ORDER_CONFIRM"] = "0"

engine = RealExecutionEngine(orders_client=DummyOrdersClient())
r = engine.execute(symbol="BRM6@RTSX", side="BUY", qty=1, price=100.0)

assert r.status == "REJECTED", r
assert "REAL_EXECUTION_ENABLED_not_enabled" in str(r.reason), r


# enabled без confirm тоже блок
os.environ["REAL_EXECUTION_ENABLED"] = "1"
os.environ["REAL_ORDER_CONFIRM"] = "0"

r = engine.execute(symbol="BRM6@RTSX", side="BUY", qty=1, price=100.0)

assert r.status == "REJECTED", r
assert "REAL_ORDER_CONFIRM_not_enabled" in str(r.reason), r


# только два флага пропускают в orders_client
os.environ["REAL_EXECUTION_ENABLED"] = "1"
os.environ["REAL_ORDER_CONFIRM"] = "1"
engine.mode = "real"

r = engine.execute(symbol="BRM6@RTSX", side="BUY", qty=1, price=100.0)

assert r.status == "ACCEPTED", r
assert r.symbol == "BRM6@RTSX", r

print("REAL_EXECUTION_SWITCH_OK")
PY
