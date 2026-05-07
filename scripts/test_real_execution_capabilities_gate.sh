#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1
export BROKER_CATEGORY=KNUR

python - <<'PY'
from finam_core.execution.real_execution import RealExecutionEngine


class FakeOrdersClient:
    def __init__(self):
        self.called = False

    def place_market_order(self, **kwargs):
        self.called = True
        return {"status": "ACCEPTED", "order_id": "fake_order_1", **kwargs}


client = FakeOrdersClient()
engine = RealExecutionEngine(client)

result = engine.execute({
    "symbol": "NGM6@RTSX",
    "side": "BUY",
    "qty": 1,
    "price": 2.5,
    "instrument_type": "FUTURE",
})

assert result.status == "REJECTED", result
assert result.reason == "futures_forbidden", result
assert client.called is False

result = engine.execute({
    "symbol": "SBER@MISX",
    "side": "SELL",
    "qty": 1,
    "price": 300,
    "instrument_type": "STOCK",
})

assert result.status == "REJECTED", result
assert result.reason == "short_forbidden", result
assert client.called is False

print("OK: RealExecutionEngine blocks forbidden live orders before broker call")
PY
