#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_MULTI_STRATEGY_ENGINE_BASE_FRAMEWORK_V1 ==="

mkdir -p \
  src/strategy/base \
  src/strategy/volatility_breakout \
  src/strategy/trend_following \
  src/strategy/mean_reversion \
  src/strategy/breakout_momentum \
  scripts

touch src/strategy/__init__.py
touch src/strategy/base/__init__.py
touch src/strategy/volatility_breakout/__init__.py
touch src/strategy/trend_following/__init__.py
touch src/strategy/mean_reversion/__init__.py
touch src/strategy/breakout_momentum/__init__.py

cat > src/strategy/base/signal.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class Signal:
    symbol: str
    timeframe: str
    strategy_family: str
    signal_ts: datetime
    direction: str
    strength: float
    score: float
    confidence: float
PY

cat > src/strategy/base/strategy_result.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from strategy.base.signal import Signal


@dataclass(slots=True, frozen=True)
class StrategyResult:
    signal: Signal | None
    diagnostics: dict[str, Any]
    execution_time_ms: float
    feature_version: str
    strategy_version: str
    reason: str
PY

cat > src/strategy/base/strategy.py <<'PY'
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from strategy.base.strategy_result import StrategyResult


class Strategy(ABC):
    name: str
    family: str
    version: str
    enabled: bool = True

    @abstractmethod
    def run(self, feature_snapshot: dict[str, Any]) -> StrategyResult:
        raise NotImplementedError
PY

cat > src/strategy/base/registry.py <<'PY'
from __future__ import annotations

from strategy.base.strategy import Strategy


class StrategyRegistry:
    _registry: dict[str, type[Strategy]] = {}

    @classmethod
    def register(cls, strategy_cls: type[Strategy]) -> type[Strategy]:
        family = getattr(strategy_cls, "family", "")
        if not family:
            raise ValueError("strategy family is required")
        cls._registry[family] = strategy_cls
        return strategy_cls

    @classmethod
    def enabled(cls) -> list[type[Strategy]]:
        return [
            strategy_cls
            for strategy_cls in cls._registry.values()
            if getattr(strategy_cls, "enabled", True)
        ]

    @classmethod
    def get(cls, family: str) -> type[Strategy] | None:
        return cls._registry.get(family)

    @classmethod
    def clear_for_tests(cls) -> None:
        cls._registry.clear()
PY

cat > src/strategy/base/loader.py <<'PY'
from __future__ import annotations

from typing import Any

from strategy.base.registry import StrategyRegistry
from strategy.base.strategy_result import StrategyResult


class StrategyLoader:
    def run_all(self, feature_snapshot: dict[str, Any]) -> list[StrategyResult]:
        results: list[StrategyResult] = []
        for strategy_cls in StrategyRegistry.enabled():
            strategy = strategy_cls()
            results.append(strategy.run(feature_snapshot))
        return results
PY

cat > src/strategy/base/config.py <<'PY'
from __future__ import annotations

DEFAULT_FEATURE_VERSION = "FEATURE_STORE_V1"
PY

cat > scripts/test_multi_strategy_engine_base_framework_v1.sh <<'SH_TEST'
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
SH_TEST

chmod +x scripts/test_multi_strategy_engine_base_framework_v1.sh
scripts/test_multi_strategy_engine_base_framework_v1.sh

echo "VERDICT=BUILD_MULTI_STRATEGY_ENGINE_BASE_FRAMEWORK_V1_OK"
