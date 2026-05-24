#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/strategy_promotion_feed.py

python - <<'PY'
from finam_core.runtime.strategy_promotion_feed import (
    StrategyPromotionInput,
    build_strategy_promotion_decision,
)

decision = build_strategy_promotion_decision(
    StrategyPromotionInput(
        symbol="BRM6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="M5",
        trade_source="paper",
        score=35.0,
        rank_status="WATCH_DIVERGENCE",
        reason="research_verdict:WATCH_DIVERGENCE",
    )
)

assert decision.runtime_action == "RESEARCH_WATCH"
assert decision.allow_paper_signal is False
assert decision.allow_radar_signal is True
assert decision.allow_real_suggestion is False
assert decision.reason == "research_watch_divergence"

print("PROMOTION_FEED_WATCH_DIVERGENCE_UNIT_OK")
PY

grep -q "WATCH_DIVERGENCE" src/finam_core/runtime/strategy_promotion_feed.py
grep -q "RESEARCH_WATCH" src/finam_core/runtime/strategy_promotion_feed.py

echo "PROMOTION_FEED_WATCH_DIVERGENCE_TEST_OK"
