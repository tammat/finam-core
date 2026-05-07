#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_EXECUTION_DECISION_LAYER=1

python - <<'PY'
from finam_core.pipelines.paper_pipeline import PaperTradingPipeline
from finam_core.execution.execution_decision_layer import ExecutionDecisionLayer


class DummyPipeline:
    _apply_execution_decision_if_enabled = PaperTradingPipeline._apply_execution_decision_if_enabled

    def __init__(self):
        self.execution_decision_layer = ExecutionDecisionLayer()


p = DummyPipeline()

intent = {
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "qty": 1,
    "signal_type": "breakout",
    "breakout_level": 103.2,
    "price": 102.8,
}

market_state = {
    "symbol": "BRM6@RTSX",
    "last": 102.8,
    "bid": 102.79,
    "ask": 102.81,
    "atr": 0.5,
}

routed = p._apply_execution_decision_if_enabled(intent, market_state)

assert routed is not None, routed
assert routed["execution_action"] == "STOP", routed
assert routed["order_type"] == "STOP", routed
assert routed["stop_price"] == 103.2, routed

wide_spread = {
    "symbol": "BRM6@RTSX",
    "last": 102.8,
    "bid": 102.0,
    "ask": 103.0,
}

blocked = p._apply_execution_decision_if_enabled(intent, wide_spread)
assert blocked is None, blocked

print("EXECUTION_DECISION_PIPELINE_OK")
PY
