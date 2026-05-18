#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/analytics/strategy_scorecard_v2.py

python - <<'PY'
from finam_core.analytics.strategy_scorecard_v2 import StrategyScorecardV2

engine = StrategyScorecardV2()

score = engine.build(
    strategy="TEST",
    trades=120,
    net_pnl=1500,
    expectancy=0.25,
    winrate=0.68,
    p_positive=0.96,
    max_drawdown=-1.2,
)

assert score.grade in ("A", "A+")
assert score.decision in ("РАЗРЕШИТЬ", "РАЗРЕШИТЬ_МАКС_КАПИТАЛ")

small = engine.build(
    strategy="TEST_SMALL",
    trades=5,
    net_pnl=10,
    expectancy=0.1,
    winrate=0.5,
    p_positive=0.6,
    max_drawdown=-0.2,
)

assert small.grade == "N"
assert small.decision == "НЕДОСТАТОЧНО_ДАННЫХ"

print("OK: strategy scorecard v2")
PY
