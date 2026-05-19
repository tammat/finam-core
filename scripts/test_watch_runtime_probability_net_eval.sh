#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/signal_probability_estimator.py \
  src/finam_core/runtime/net_trade_evaluator.py \
  src/scripts/analyze_watch_candidates_runtime.py

grep -q "apply_net_trade_evaluation" src/scripts/analyze_watch_candidates_runtime.py
grep -q "estimate_signal_probability" src/scripts/analyze_watch_candidates_runtime.py
grep -q "expected_value" src/scripts/analyze_watch_candidates_runtime.py

echo "OK: watch runtime probability net evaluation"
