#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_MANUAL_POSITION_TELEGRAM_ADVISORY_V1_START"

TMP_LOG="$(mktemp)"

python src/scripts/analytics/build_manual_position_telegram_advisory_v1.py \
  2>&1 | tee "$TMP_LOG"

grep -q "MANUAL_POSITION_TELEGRAM_ADVISORY_V1" "$TMP_LOG"
grep -q "MANUAL_POSITION_TELEGRAM_ADVISORY_SUMMARY" "$TMP_LOG"
grep -q "MANUAL_POSITION_TELEGRAM_ADVISORY_V1_OK" "$TMP_LOG"

echo "TEST_MANUAL_POSITION_TELEGRAM_ADVISORY_V1_OK"
