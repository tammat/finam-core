#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.strategy_ranking_v2 import (
    StrategyRankingInputV2,
    calculate_strategy_rank_v2,
)

good = calculate_strategy_rank_v2(
    StrategyRankingInputV2(
        symbol="PLZL@MISX",
        strategy="TEST",
        timeframe="M5",
        trade_source="paper",
        trades=80,
        profit_factor=1.6,
        winrate=0.58,
        expectancy=12.0,
        quality_full_ratio=0.8,
        risk_context_weak_ratio=0.0,
        high_heat_ratio=0.1,
        lifecycle_problem_ratio=0.0,
        status="PROMISING",
    )
)

assert good.score > 25
assert good.rank_status == "PROMOTE"

low = calculate_strategy_rank_v2(
    StrategyRankingInputV2(
        symbol="PLZL@MISX",
        strategy="LOW",
        timeframe="M5",
        trade_source="paper",
        trades=5,
        profit_factor=5.0,
        winrate=1.0,
        expectancy=100.0,
        quality_full_ratio=1.0,
        risk_context_weak_ratio=0.0,
        high_heat_ratio=0.0,
        lifecycle_problem_ratio=0.0,
        status="PROMISING",
    )
)

assert low.rank_status == "WATCH_LOW_SAMPLE"

print("TEST_STRATEGY_RANKING_V2_OK")
PY

python -m py_compile \
  src/finam_core/analytics/strategy_ranking_v2.py \
  src/finam_core/analytics/strategy_ranking_v2_repository.py \
  src/scripts/build_strategy_ranking_v2.py
