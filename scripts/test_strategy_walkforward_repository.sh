#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/walkforward_repository.py \
  src/scripts/research/build_strategy_walkforward.py

python - <<'PY'
from datetime import datetime, timezone, timedelta

from finam_core.research.walkforward_repository import StrategyWalkForwardRepository

repo = StrategyWalkForwardRepository(database_url="")
base = datetime(2026, 1, 1, tzinfo=timezone.utc)

rows = []
for i in range(40):
    pnl = 2.0 if i % 2 == 0 else -1.0
    rows.append((pnl, base + timedelta(minutes=i)))

res = repo._build_result(
    ("S", "BRM6@RTSX", "M5", "LOW_IMPULSE", "paper"),
    rows[:28],
    rows[28:],
)

assert res.train_trades == 28
assert res.test_trades == 12
assert res.test_pf > 1.0
assert res.status in {"OOS_CONFIRMED", "OOS_WATCH", "OOS_FAILED"}

print("STRATEGY_WALKFORWARD_REPOSITORY_UNIT_OK")
PY

grep -q "trade_attribution_v2" src/finam_core/research/walkforward_repository.py
grep -q "strategy_walkforward_results" src/finam_core/research/walkforward_repository.py
grep -q "STRATEGY_WALKFORWARD_BUILD_OK" src/scripts/research/build_strategy_walkforward.py

echo "STRATEGY_WALKFORWARD_REPOSITORY_TEST_OK"
