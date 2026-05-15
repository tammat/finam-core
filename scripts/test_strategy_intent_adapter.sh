#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/signals/signal_intent.py \
  src/finam_core/signals/strategy_intent_adapter.py

python - <<'PY'
from finam_core.signals.signal_intent import SignalIntent
from finam_core.signals.strategy_intent_adapter import StrategyIntentAdapter


# =========================================================
# legacy dict -> SignalIntent
# =========================================================

legacy = {
    "symbol": "BRM6@RTSX",
    "side": "BUY",
    "qty": 1,
    "price": 108.5,
    "strategy": "BR_CONSERVATIVE_BREAKOUT",
    "features": {
        "stop": 108.0,
        "take": 109.2,
    }
}

intent = StrategyIntentAdapter.normalize(legacy)

assert isinstance(intent, SignalIntent)
assert intent.symbol == "BRM6@RTSX"
assert intent.continuous_symbol == "BR_CONT"
assert intent.entry_price == 108.5
assert intent.stop_price == 108.0
assert intent.take_profit == 109.2


# =========================================================
# SignalIntent passthrough
# =========================================================

original = SignalIntent(
    symbol="PLZL@MISX",
    side="SELL",
    strategy="TREND_PULLBACK_EQUITY",
    entry_price=2135.0,
)

same = StrategyIntentAdapter.normalize(original)

assert same is original


# =========================================================
# pipeline dict compatibility
# =========================================================

pipeline_dict = StrategyIntentAdapter.to_pipeline_dict(intent)

assert pipeline_dict["symbol"] == "BRM6@RTSX"
assert pipeline_dict["continuous_symbol"] == "BR_CONT"
assert pipeline_dict["strategy"] == "BR_CONSERVATIVE_BREAKOUT"
assert pipeline_dict["price"] == 108.5
assert pipeline_dict["features"]["stop"] == 108.0


# =========================================================
# None passthrough
# =========================================================

assert StrategyIntentAdapter.normalize(None) is None
assert StrategyIntentAdapter.to_pipeline_dict(None) is None


# =========================================================
# invalid type
# =========================================================

try:
    StrategyIntentAdapter.normalize(123)
    raise AssertionError("Expected TypeError")
except TypeError:
    pass

print("OK: StrategyIntentAdapter works")
PY
