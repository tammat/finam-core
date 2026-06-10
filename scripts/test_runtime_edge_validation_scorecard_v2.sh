#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_edge_validation_scorecard_v2.py

python3 \
  src/scripts/analytics/build_runtime_edge_validation_scorecard_v2.py \
  | tee /tmp/runtime_edge_validation_scorecard_v2.log

grep -q "RUNTIME EDGE VALIDATION SCORECARD V2" \
  /tmp/runtime_edge_validation_scorecard_v2.log

grep -q "EDGE_ROWS" \
  /tmp/runtime_edge_validation_scorecard_v2.log

grep -q "strategy=BR_RUNTIME" \
  /tmp/runtime_edge_validation_scorecard_v2.log

grep -q "governance_decision=WATCH_ONLY" \
  /tmp/runtime_edge_validation_scorecard_v2.log

grep -q "strategy=GOLD_SHORT_ONLY" \
  /tmp/runtime_edge_validation_scorecard_v2.log

grep -q "RUNTIME_EDGE_VALIDATION_SCORECARD_V2_OK" \
  /tmp/runtime_edge_validation_scorecard_v2.log

echo TEST_RUNTIME_EDGE_VALIDATION_SCORECARD_V2_OK
