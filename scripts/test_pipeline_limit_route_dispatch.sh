#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline

calls = []

class FakeDispatcher:
    def place_limit_order(self, **kwargs):
        calls.append(kwargs)
        return {"status": "DRY_RUN_ACCEPTED", "reason": "test", "order_id": "dry1"}

pipe = PaperTradingPipeline.__new__(PaperTradingPipeline)
pipe.execution_dispatcher = FakeDispatcher()

handled = pipe._execute_routed_order_if_needed(
    {
        "order_route": "LIMIT_ORDER",
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 1,
        "limit_price": 80.01,
        "entry_price": 80.01,
        "stop_loss": 79.26,
        "take_profit": 81.01,
    },
    {"last": 80.0},
)

assert handled is True
assert len(calls) == 1, calls
assert calls[0]["symbol"] == "BRM6@RTSX"
assert calls[0]["side"] == "BUY"
assert calls[0]["qty"] == 1.0
assert calls[0]["limit_price"] == 80.01

handled2 = pipe._execute_routed_order_if_needed(
    {"order_route": "REAL_EXECUTION", "symbol": "BRM6@RTSX", "side": "BUY", "qty": 1},
    {"last": 80.0},
)

assert handled2 is False

print("PIPELINE_LIMIT_ROUTE_DISPATCH_OK")
PY
