#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_CLOSED_TRADE_QUALITY_AUDIT_V1_START"

python -m py_compile src/scripts/analytics/build_closed_trade_quality_audit_v1.py

python src/scripts/analytics/build_closed_trade_quality_audit_v1.py \
  --window-days 365 \
  --outlier-pct 0.20 \
  --min-batch-rows 20 | tee /tmp/closed_trade_quality_audit_v1.out

grep -q "CLOSED_TRADE_QUALITY_AUDIT_V1" /tmp/closed_trade_quality_audit_v1.out
grep -q "CLOSED_TRADE_QUALITY_SUMMARY" /tmp/closed_trade_quality_audit_v1.out
grep -q "CLOSED_TRADE_SUSPECT_BATCH" /tmp/closed_trade_quality_audit_v1.out
grep -q "CLOSED_TRADE_QUALITY_AUDIT_V1_OK" /tmp/closed_trade_quality_audit_v1.out

echo "TEST_CLOSED_TRADE_QUALITY_AUDIT_V1_OK"
