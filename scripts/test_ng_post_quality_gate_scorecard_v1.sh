#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_ng_post_quality_gate_scorecard_v1.py

python3 src/scripts/analytics/build_ng_post_quality_gate_scorecard_v1.py \
  | tee /tmp/ng_post_quality_gate_scorecard_v1.log

grep -q "NG POST QUALITY GATE SCORECARD V1" /tmp/ng_post_quality_gate_scorecard_v1.log
grep -q "GATE_SUMMARY" /tmp/ng_post_quality_gate_scorecard_v1.log
grep -q "POST_GATE_CLOSED_SUMMARY" /tmp/ng_post_quality_gate_scorecard_v1.log
grep -q "POST_GATE_FILLS" /tmp/ng_post_quality_gate_scorecard_v1.log
grep -q "NG_POST_QUALITY_GATE_SCORECARD_V1_OK" /tmp/ng_post_quality_gate_scorecard_v1.log

echo "TEST_NG_POST_QUALITY_GATE_SCORECARD_V1_OK"
