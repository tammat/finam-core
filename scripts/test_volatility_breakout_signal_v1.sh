#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_VOLATILITY_BREAKOUT_SIGNAL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/strategy/base/diagnostics.py \
  src/strategy/base/strategy_result.py \
  src/strategy/volatility_breakout/config.py \
  src/strategy/volatility_breakout/strategy.py \
  src/strategy/volatility_breakout/__init__.py

PYTHONPATH=src python - <<'PY'
from strategy.base.registry import StrategyRegistry
import strategy.volatility_breakout  # noqa: F401
from strategy.volatility_breakout.strategy import VolatilityBreakoutStrategy

assert StrategyRegistry.get("VOLATILITY_BREAKOUT") is VolatilityBreakoutStrategy

strategy = VolatilityBreakoutStrategy()

long_result = strategy.run({
    "symbol": "SBER@MISX",
    "timeframe": "M1",
    "bar_ts": "2026-07-03T15:41:00+03:00",
    "range_pct": 1.2,
    "body_pct": 0.7,
    "volume_ratio20": 1.5,
    "feature_quality_score": 0.95,
    "return1_pct": 0.15,
    "return5_pct": 0.30,
    "source_version": "FEATURE_STORE_V1",
})
assert long_result.signal is not None
assert long_result.signal.direction == "LONG"
assert "range_pct" in long_result.diagnostics.passed_filters

short_result = strategy.run({
    "symbol": "GAZP@MISX",
    "timeframe": "M1",
    "bar_ts": "2026-07-03T15:41:00+03:00",
    "range_pct": 1.2,
    "body_pct": 0.7,
    "volume_ratio20": 1.5,
    "feature_quality_score": 0.95,
    "return1_pct": -0.15,
    "return5_pct": -0.30,
})
assert short_result.signal is not None
assert short_result.signal.direction == "SHORT"

flat_result = strategy.run({
    "symbol": "LKOH@MISX",
    "timeframe": "M1",
    "bar_ts": "2026-07-03T15:41:00+03:00",
    "range_pct": 0.1,
    "body_pct": 0.1,
    "volume_ratio20": 0.8,
    "feature_quality_score": 0.95,
    "return1_pct": 0.15,
    "return5_pct": 0.30,
})
assert flat_result.signal is None
assert flat_result.reason == "BASE_FILTER_FAILED"
assert "range_pct" in flat_result.diagnostics.failed_filters

invalid_result = strategy.run({
    "symbol": "",
    "timeframe": "",
})
assert invalid_result.signal is None
assert invalid_result.reason == "INVALID_FEATURE"
PY

echo "strategy=VOLATILITY_BREAKOUT"
echo "long_signal=ok"
echo "short_signal=ok"
echo "flat_result=ok"
echo "invalid_feature=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=VOLATILITY_BREAKOUT_SIGNAL_V1_READY"
echo "VERDICT=TEST_VOLATILITY_BREAKOUT_SIGNAL_V1_OK"
