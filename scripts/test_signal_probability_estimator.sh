#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/signal_probability_estimator.py

python - <<'PY'
from finam_core.runtime.signal_probability_estimator import SignalProbabilityEstimator

p = SignalProbabilityEstimator().estimate(
    tp_hits=58,
    sl_hits=31,
    expired=11,
)

assert p.sample_size == 100
assert abs(p.probability_tp - 0.58) < 0.01
assert abs(p.probability_sl - 0.31) < 0.01

print("OK: signal probability estimator")
PY
