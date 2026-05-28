#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_EDGE_GATE_PRODUCTION_STATUS_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_edge_gate_production_status_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "EDGE_GATE_PRODUCTION_STATUS_V1" "$TMP_LOG"
grep -q "EDGE_GATE_PRODUCTION_STATUS" "$TMP_LOG"
grep -q "EDGE_GATE_PRODUCTION_WIRING" "$TMP_LOG"
grep -q "EDGE_GATE_PRODUCTION_AUDIT" "$TMP_LOG"
grep -q "EDGE_GATE_PRODUCTION_STATUS_V1_OK" "$TMP_LOG"

echo "TEST_EDGE_GATE_PRODUCTION_STATUS_V1_OK"
