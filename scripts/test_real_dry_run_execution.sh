#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real_dry_run
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1

python - <<'PY'
from finam_core.execution.real_execution import RealExecutionEngine


class DummyOrdersClient:
    def place_market_order(self, *args, **kwargs):
        raise RuntimeError("REAL ORDER MUST NOT BE CALLED IN real_dry_run")


engine = RealExecutionEngine(orders_client=DummyOrdersClient())

intent = {
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "qty": 1.0,
    "price": 102.15,
}

result = engine.execute(intent, {"last": 102.15})

assert result.status == "DRY_RUN_ACCEPTED", result
assert result.symbol == "BRM6@RTSX", result
assert result.side == "BUY", result
assert float(result.qty) == 1.0, result
assert result.order_id, result
assert str(result.order_id).startswith(("dry_", "local_")), result

print(
    f"PIPE_REAL_EXECUTION_RESULT mode=real_dry_run "
    f"symbol={result.symbol} side={result.side} "
    f"qty={result.qty} price={result.price} status={result.status}"
)

print("REAL_DRY_RUN_EXECUTION_OK")
PY
