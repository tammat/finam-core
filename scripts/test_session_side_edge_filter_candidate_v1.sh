#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_session_side_edge_filter_candidate_v1.py

python3 src/scripts/analytics/build_session_side_edge_filter_candidate_v1.py \
  --symbols BRM6@RTSX,BRN6@RTSX,NGN6@RTSX \
  --trade-source paper \
  | tee /tmp/session_side_edge_filter_candidate_v1.log

grep -q "SESSION SIDE EDGE FILTER CANDIDATE V1" /tmp/session_side_edge_filter_candidate_v1.log
grep -q "CANDIDATE_ROWS" /tmp/session_side_edge_filter_candidate_v1.log
grep -q "SUMMARY_ROW" /tmp/session_side_edge_filter_candidate_v1.log
grep -q "SESSION_SIDE_EDGE_FILTER_CANDIDATE_V1_OK" /tmp/session_side_edge_filter_candidate_v1.log

echo "TEST_SESSION_SIDE_EDGE_FILTER_CANDIDATE_V1_OK"
