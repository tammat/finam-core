#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/performance_snapshot.py \
  src/finam_core/research/strategy_performance_repository.py \
  src/scripts/research/build_strategy_performance.py

python - <<'PY'
from finam_core.research.strategy_performance_repository import StrategyPerformanceRepository

repo = StrategyPerformanceRepository(database_url="")
snap = repo._build_snapshot(
    ("S", "BRM6@RTSX", "M5", "LOW_IMPULSE", "paper"),
    [
        {"pnl": 10.0, "context_quality": "FULL", "hold_sec": 60},
        {"pnl": -5.0, "context_quality": "FULL", "hold_sec": 120},
        {"pnl": 15.0, "context_quality": "FULL", "hold_sec": 180},
    ],
)

assert snap.trades == 3
assert snap.wins == 2
assert snap.losses == 1
assert round(snap.net_pnl, 4) == 20.0
assert round(snap.profit_factor, 4) == 5.0
assert snap.context_quality == "FULL"
assert snap.status == "LOW_SAMPLE"

print("STRATEGY_PERFORMANCE_REPOSITORY_UNIT_OK")
PY

grep -q "trade_attribution_v2" src/finam_core/research/strategy_performance_repository.py
grep -q "trade_context_snapshots" src/finam_core/research/strategy_performance_repository.py
grep -q "strategy_performance" src/finam_core/research/strategy_performance_repository.py
grep -q "STRATEGY_PERFORMANCE_BUILD_OK" src/scripts/research/build_strategy_performance.py

echo "STRATEGY_PERFORMANCE_REPOSITORY_TEST_OK"
