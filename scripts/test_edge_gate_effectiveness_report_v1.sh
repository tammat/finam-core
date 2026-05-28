#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_EDGE_GATE_EFFECTIVENESS_REPORT_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_edge_gate_effectiveness_report_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "EDGE_GATE_EFFECTIVENESS_REPORT_V1" "$TMP_LOG"
grep -q "EDGE_GATE_EFFECTIVENESS_STATUS" "$TMP_LOG"
grep -q "EDGE_GATE_EFFECTIVENESS_BUCKET" "$TMP_LOG"
grep -q "EDGE_GATE_EFFECTIVENESS_DELTA" "$TMP_LOG"
grep -q "EDGE_GATE_EFFECTIVENESS_ROW" "$TMP_LOG"
grep -q "EDGE_GATE_EFFECTIVENESS_REPORT_V1_OK" "$TMP_LOG"

echo "TEST_EDGE_GATE_EFFECTIVENESS_REPORT_V1_OK"
