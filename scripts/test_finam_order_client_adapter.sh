#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/execution/finam_order_client_adapter.py

python - <<'PY'
from finam_core.execution.finam_order_client_adapter import FinamOrderClientAdapter


class Client:
    def place_limit_order(self, **kwargs):
        assert kwargs["side"] in {"BUY", "SELL"}
        assert "limit_price" in kwargs
        return {"order_id": "TEST123"}


r = FinamOrderClientAdapter(Client()).place_buy_limit(
    symbol="SBER@MISX",
    qty=1,
    price=300,
)

assert r.ok is True
assert r.broker_order_id == "TEST123"

s = FinamOrderClientAdapter(Client()).place_sell_limit(
    symbol="SBER@MISX",
    qty=1,
    price=326.5,
)

assert s.ok is True
assert s.broker_order_id == "TEST123"

print("OK: finam order client adapter")
PY
