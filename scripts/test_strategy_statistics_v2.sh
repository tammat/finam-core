#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.strategy_statistics_v2 import (
    StrategyTradeSampleV2,
    calculate_strategy_statistics_v2,
)

stats = calculate_strategy_statistics_v2(
    symbol="PLZL@MISX",
    strategy="TEST",
    timeframe="M5",
    trade_source="paper",
    trades=[
        StrategyTradeSampleV2(10, "FULL", "HIGH", "NO_ACTION"),
        StrategyTradeSampleV2(-5, "PARTIAL", "unknown", "NO_ACTION"),
        StrategyTradeSampleV2(15, "FULL", "LOW", "NO_ACTION"),
    ],
)

assert stats.trades == 3
assert stats.wins == 2
assert round(stats.winrate, 4) == 0.6667
assert stats.expectancy > 0
assert stats.status == "LOW_SAMPLE"

print("TEST_STRATEGY_STATISTICS_V2_OK")
PY

python -m py_compile \
  src/finam_core/analytics/strategy_statistics_v2.py \
  src/finam_core/analytics/strategy_statistics_v2_repository.py \
  src/scripts/build_strategy_statistics_v2.py
