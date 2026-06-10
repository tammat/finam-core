#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_session_regime_edge_matrix_v1.py

python3 src/scripts/analytics/build_session_regime_edge_matrix_v1.py \
  --symbols BRM6@RTSX,BRN6@RTSX,NGN6@RTSX \
  --trade-source paper \
  | tee /tmp/session_regime_edge_matrix_v1.log

grep -q "SESSION REGIME EDGE MATRIX V1" /tmp/session_regime_edge_matrix_v1.log
grep -q "SESSION_REGIME_ROWS" /tmp/session_regime_edge_matrix_v1.log
grep -q "SUMMARY_ROW" /tmp/session_regime_edge_matrix_v1.log
grep -q "SESSION_REGIME_EDGE_MATRIX_V1_OK" /tmp/session_regime_edge_matrix_v1.log

echo "TEST_SESSION_REGIME_EDGE_MATRIX_V1_OK"
