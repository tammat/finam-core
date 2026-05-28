#!/usr/bin/env bash
set -euo pipefail

python -m py_compile src/finam_core/runtime/strategy_promotion_feed.py

python - <<'PY'
from finam_core.runtime.strategy_promotion_feed import (
    StrategyPromotionInput,
    build_strategy_promotion_decision,
)

d = build_strategy_promotion_decision(
    StrategyPromotionInput(
        symbol="BRN6@RTSX",
        strategy="BR_CONSERVATIVE_BREAKOUT",
        timeframe="M5",
        trade_source="paper",
        score=72.0,
        rank_status="CANDIDATE",
        reason="research_verdict:CANDIDATE",
    )
)

assert d.runtime_action == "PAPER_CANDIDATE", d
assert d.allow_paper_signal is True, d
assert d.allow_radar_signal is True, d
assert d.allow_real_suggestion is False, d

print("STRATEGY_PROMOTION_FEED_CANDIDATE_UNIT_OK")
PY

grep -q 'status == "CANDIDATE"' src/finam_core/runtime/strategy_promotion_feed.py
grep -q 'runtime_action="PAPER_CANDIDATE"' src/finam_core/runtime/strategy_promotion_feed.py

echo "STRATEGY_PROMOTION_FEED_CANDIDATE_TEST_OK"
