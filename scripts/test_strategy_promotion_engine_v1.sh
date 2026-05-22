#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.runtime.strategy_promotion_engine_v1 import (
    StrategyPromotionEngineInput,
    decide_strategy_promotion_v1,
)

good = decide_strategy_promotion_v1(
    StrategyPromotionEngineInput(
        symbol="BRM6@RTSX",
        strategy="br_conservative_breakout",
        timeframe="M5",
        trade_source="paper",
        trades=80,
        profit_factor=1.6,
        expectancy=10,
        winrate=0.58,
        score=40,
        rank_status="PROMOTE",
        fill_quality_status="RECONSTRUCTION_ALLOWED",
        reconstruction_allowed=True,
        lifecycle_state="RADAR",
    )
)
assert good.decision == "PROMOTE_TO_PAPER"
assert good.target_lifecycle_state == "PAPER"
assert good.allow_runtime is True

bad_quality = decide_strategy_promotion_v1(
    StrategyPromotionEngineInput(
        symbol="NGK6@RTSX",
        strategy="ng_volatility_breakout",
        timeframe="M5",
        trade_source="paper",
        trades=100,
        profit_factor=2,
        expectancy=10,
        winrate=0.7,
        score=50,
        rank_status="PROMOTE",
        fill_quality_status="ONE_SIDED_FILLS",
        reconstruction_allowed=False,
        lifecycle_state="UNKNOWN",
    )
)
assert bad_quality.decision == "BLOCK"
assert bad_quality.target_lifecycle_state == "BLOCKED"

print("TEST_STRATEGY_PROMOTION_ENGINE_V1_OK")
PY

python -m py_compile \
  src/finam_core/runtime/strategy_promotion_engine_v1.py \
  src/finam_core/runtime/strategy_promotion_engine_repository.py \
  src/scripts/build_strategy_promotion_engine_v1.py
