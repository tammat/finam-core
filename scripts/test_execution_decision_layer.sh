#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.execution.execution_decision_layer import ExecutionDecisionLayer

layer = ExecutionDecisionLayer()

d = layer.decide(
    {"symbol": "BRM6@RTSX", "side": "SELL", "qty": 1, "intent_type": "EXIT", "price": 102.0},
    {"last": 102.0, "bid": 101.99, "ask": 102.01},
)
assert d.action == "MARKET", d
assert d.reason == "exit_or_emergency_market", d

d = layer.decide(
    {
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 1,
        "signal_type": "breakout",
        "breakout_level": 103.2,
        "price": 102.8,
    },
    {"last": 102.8, "bid": 102.79, "ask": 102.81, "atr": 0.5},
)
assert d.action == "STOP", d
assert d.stop_price == 103.2, d

d = layer.decide(
    {
        "symbol": "BRM6@RTSX",
        "side": "BUY",
        "qty": 1,
        "price": 103.4,
        "atr": 0.5,
        "range_atr": 2.5,
        "volume_ratio": 2.0,
        "regime": "trend_up",
        "allow_market_on_impulse": True,
    },
    {"last": 103.4, "bid": 103.39, "ask": 103.41},
)
assert d.action == "MARKET", d
assert d.reason == "confirmed_impulse_market", d

d = layer.decide(
    {"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "signal_type": "breakout", "breakout_level": 103.2},
    {"last": 102.8, "bid": 102.0, "ask": 103.0},
)
assert d.action == "SKIP", d
assert "spread_too_wide" in d.reason, d

d = layer.decide(
    {"symbol": "BRM6@RTSX", "side": "BUY", "qty": 1, "signal_type": "pullback", "limit_price": 102.1},
    {"last": 102.4, "bid": 102.39, "ask": 102.41},
)
assert d.action == "LIMIT", d
assert d.limit_price == 102.1, d

print("EXECUTION_DECISION_LAYER_OK")
PY
