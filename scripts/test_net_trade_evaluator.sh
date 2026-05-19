#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/net_trade_evaluator.py

python - <<'PY'
from finam_core.runtime.net_trade_evaluator import NetTradeEvaluator

r = NetTradeEvaluator().evaluate(
    entry_price=2445,
    stop_loss=2408,
    take_profit=2518,
    qty=10,

    probability_tp=0.58,
    probability_sl=0.42,
)

assert r.expected_value > 0
assert r.net_take_profit > 0
assert r.net_stop_loss > 0

print("OK: net trade evaluator")
PY
