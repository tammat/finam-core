#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.runtime.strategy_promotion_feed import (
    StrategyPromotionInput,
    build_strategy_promotion_decision,
)

promote = build_strategy_promotion_decision(
    StrategyPromotionInput(
        symbol="PLZL@MISX",
        strategy="TEST",
        timeframe="M5",
        trade_source="paper",
        score=40,
        rank_status="PROMOTE",
        reason="ok",
    )
)
assert promote.allow_paper_signal is True
assert promote.allow_radar_signal is True
assert promote.allow_real_suggestion is False

watch = build_strategy_promotion_decision(
    StrategyPromotionInput(
        symbol="PLZL@MISX",
        strategy="TEST",
        timeframe="M5",
        trade_source="paper",
        score=10,
        rank_status="WATCH",
        reason="watch",
    )
)
assert watch.allow_paper_signal is False
assert watch.allow_radar_signal is True

reject = build_strategy_promotion_decision(
    StrategyPromotionInput(
        symbol="PLZL@MISX",
        strategy="BAD",
        timeframe="M5",
        trade_source="paper",
        score=0,
        rank_status="REJECT",
        reason="bad",
    )
)
assert reject.runtime_action == "BLOCK"

print("TEST_STRATEGY_PROMOTION_FEED_OK")
PY

python -m py_compile \
  src/finam_core/runtime/strategy_promotion_feed.py \
  src/scripts/build_strategy_promotion_feed.py
