#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PRE_SIGNAL_BLOCK_DRIFT_REPORT_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_pre_signal_block_drift_report_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "PRE_SIGNAL_BLOCK_DRIFT_REPORT_V1" "$TMP_LOG"

grep -q "PRE_SIGNAL_BLOCK_DRIFT_REPORT_V1_OK" "$TMP_LOG"

echo "TEST_PRE_SIGNAL_BLOCK_DRIFT_REPORT_V1_OK"
