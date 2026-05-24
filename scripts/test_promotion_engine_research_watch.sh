#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/strategy_promotion_engine_v1.py

python - <<'PY'
from finam_core.runtime.strategy_promotion_engine_v1 import (
    StrategyPromotionEngineInput,
    decide_strategy_promotion_v1,
)

decision = decide_strategy_promotion_v1(
    StrategyPromotionEngineInput(
        symbol="BRM6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="M5",
        trade_source="paper",
        trades=104,
        profit_factor=0.9281,
        expectancy=-0.2368,
        winrate=0.3365,
        quality_full_ratio=1.0,
        quality_partial_ratio=0.0,
        risk_context_weak_ratio=0.0,
        score=35.0,
        rank_status="WATCH_DIVERGENCE",
        fill_quality_status="RECONSTRUCTION_ALLOWED",
        reconstruction_allowed=True,
        lifecycle_state="RESEARCH_WATCH",
    )
)

assert decision.decision == "KEEP_RESEARCH_WATCH"
assert decision.target_lifecycle_state == "RESEARCH_WATCH"
assert decision.allow_runtime is False
assert decision.allow_radar is True
assert decision.allow_research is True
assert decision.reason == "research_watch_divergence"

print("PROMOTION_ENGINE_RESEARCH_WATCH_UNIT_OK")
PY

grep -q "KEEP_RESEARCH_WATCH" src/finam_core/runtime/strategy_promotion_engine_v1.py
grep -q "RESEARCH_WATCH" src/finam_core/runtime/strategy_promotion_engine_v1.py

echo "PROMOTION_ENGINE_RESEARCH_WATCH_TEST_OK"
