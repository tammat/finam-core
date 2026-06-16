#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/finam_core/runtime/strategy_promotion_feed.py

python3 - <<'PY'
from finam_core.runtime.strategy_promotion_feed import (
    StrategyPromotionInput,
    build_strategy_promotion_decision,
)

item = StrategyPromotionInput(
    symbol="PLZL@MISX",
    strategy="MOEX_SIMPLE_MOMENTUM",
    timeframe="D1",
    trade_source="paper",
    score=0.0,
    rank_status="REJECT",
    reason="test_reject_but_attribution_chain_confirmed",
)

d = build_strategy_promotion_decision(item)

assert d.runtime_action == "RESEARCH_WATCH", d
assert d.allow_paper_signal is False, d
assert d.allow_radar_signal is True, d
assert d.allow_real_suggestion is False, d
assert d.reason.startswith("plzl_attribution_chain_research_watch:"), d

bad = StrategyPromotionInput(
    symbol="LKOH@MISX",
    strategy="MOEX_SIMPLE_MOMENTUM",
    timeframe="D1",
    trade_source="paper",
    score=0.0,
    rank_status="REJECT",
    reason="negative_edge",
)

bd = build_strategy_promotion_decision(bad)
assert bd.runtime_action == "BLOCK", bd
assert bd.allow_radar_signal is False, bd

print("TEST_STRATEGY_PROMOTION_FEED_PLZL_RESEARCH_WATCH_V1_OK")
PY
