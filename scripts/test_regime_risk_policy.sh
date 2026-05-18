#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/regime_risk_policy.py \
  src/scripts/build_regime_risk_policy.py

python src/scripts/build_regime_risk_policy.py --help >/dev/null

python - <<'PY'
from finam_core.research.regime_risk_policy import (
    RegimePerformance,
    RegimeRiskPolicy,
)

items = [
    RegimePerformance("range:normal_vol", "range", "normal_vol", 10, 100, 10, 0.6),
    RegimePerformance("trend_down:high_vol", "trend_down", "high_vol", 10, -50, -5, 0.3),
    RegimePerformance("squeeze:low_vol", "squeeze", "low_vol", 2, 10, 5, 1.0),
]

decisions = RegimeRiskPolicy().decide(items, min_trades=5)

assert decisions[0].decision == "РАЗРЕШИТЬ"
assert decisions[1].decision == "ЗАПРЕТИТЬ"
assert decisions[2].decision == "НЕДОСТАТОЧНО_ДАННЫХ"

print("OK: regime risk policy")
PY
