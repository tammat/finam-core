#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/institutional_trade_quality_score.py \
  src/scripts/analyze_watch_candidates_runtime.py

python - <<'PY'
from finam_core.runtime.institutional_trade_quality_score import InstitutionalTradeQualityScorer

s = InstitutionalTradeQualityScorer().score(
    probability_tp=0.58,
    probability_sl=0.31,
    expected_value_pct=1.2,
    risk_reward=2.0,
    signal_score=3.5,
    correlation_pressure=0,
    risk_multiplier=1.2,
)

assert s.score > 0
assert s.grade in {"A", "B", "C", "D"}

print("OK: institutional trade quality score")
PY
