#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_EDGE_GATE_RUNTIME_ROLLOUT_CHECK_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_edge_gate_runtime_rollout_check_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "EDGE_GATE_RUNTIME_ROLLOUT_CHECK_V1" "$TMP_LOG"
grep -q "EDGE_GATE_RUNTIME_ROLLOUT_CHECK_STATUS" "$TMP_LOG"
grep -q "EDGE_GATE_RUNTIME_ROLLOUT_CHECK_WIRING" "$TMP_LOG"
grep -q "EDGE_GATE_RUNTIME_ROLLOUT_CHECK_V1_OK" "$TMP_LOG"

echo "TEST_EDGE_GATE_RUNTIME_ROLLOUT_CHECK_V1_OK"
