#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/adaptive_strategy_weighting_engine.py

python - <<'PY'
from finam_core.analytics.adaptive_strategy_weighting_engine import (
    AdaptiveStrategyWeightingEngine,
    StrategyWeightInput,
)

engine = AdaptiveStrategyWeightingEngine(min_qty=0.01)

strong = engine.decide(StrategyWeightInput(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT_M5",
    health_score=82,
    status="УСИЛИТЬ",
    base_qty=2,
    regime="trend_high_vol",
))

assert strong.allow_trade is True
assert strong.watch_only is False
assert strong.size_multiplier == 1.5
assert strong.adjusted_qty == 3.0

weak = engine.decide(StrategyWeightInput(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT_M5",
    health_score=20,
    status="УСИЛИТЬ",
    base_qty=4,
))

assert weak.allow_trade is True
assert weak.size_multiplier == 0.25
assert weak.adjusted_qty == 1.0

disabled = engine.decide(StrategyWeightInput(
    symbol="BRM6@RTSX",
    strategy="BAD_STRATEGY",
    health_score=10,
    status="ОТКЛЮЧИТЬ",
    base_qty=5,
))

assert disabled.allow_trade is False
assert disabled.watch_only is True
assert disabled.adjusted_qty == 0.0

print("OK: адаптивное взвешивание стратегий работает")
PY
