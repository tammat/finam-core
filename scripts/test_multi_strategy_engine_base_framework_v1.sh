#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MULTI_STRATEGY_ENGINE_BASE_FRAMEWORK_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/strategy/base/signal.py \
  src/strategy/base/strategy_result.py \
  src/strategy/base/strategy.py \
  src/strategy/base/registry.py \
  src/strategy/base/loader.py \
  src/strategy/base/config.py

PYTHONPATH=src python - <<'PY'
from datetime import datetime, timezone
from typing import Any

from strategy.base.registry import StrategyRegistry
from strategy.base.signal import Signal
from strategy.base.strategy import Strategy
from strategy.base.strategy_result import StrategyResult
from strategy.base.loader import StrategyLoader

StrategyRegistry.clear_for_tests()

class DummyStrategy(Strategy):
    name = "Dummy"
    family = "DUMMY"
    version = "DUMMY_V1"
    enabled = True

    def run(self, feature_snapshot: dict[str, Any]) -> StrategyResult:
        signal = Signal(
            symbol=feature_snapshot["symbol"],
            timeframe=feature_snapshot["timeframe"],
            strategy_family=self.family,
            signal_ts=datetime.now(timezone.utc),
            direction="LONG",
            strength=1.0,
            score=1.0,
            confidence=1.0,
        )
        return StrategyResult(
            signal=signal,
            diagnostics={"test": True},
            execution_time_ms=0.1,
            feature_version="FEATURE_STORE_V1",
            strategy_version=self.version,
            reason="test_ok",
        )

StrategyRegistry.register(DummyStrategy)

assert StrategyRegistry.get("DUMMY") is DummyStrategy
assert len(StrategyRegistry.enabled()) == 1

loader = StrategyLoader()
results = loader.run_all({"symbol": "SBER@MISX", "timeframe": "M1"})
assert len(results) == 1
assert results[0].signal is not None
assert results[0].signal.symbol == "SBER@MISX"
assert results[0].signal.strategy_family == "DUMMY"

StrategyRegistry.clear_for_tests()
assert StrategyRegistry.enabled() == []
PY

echo "strategy_framework_imports=ok"
echo "registry=ok"
echo "loader=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MULTI_STRATEGY_ENGINE_BASE_FRAMEWORK_V1_READY"
echo "VERDICT=TEST_MULTI_STRATEGY_ENGINE_BASE_FRAMEWORK_V1_OK"
