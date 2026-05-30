#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_TRADES_QUALITY_AUDIT_V1_START"

python -m py_compile src/scripts/analytics/build_trades_quality_audit_v1.py

python src/scripts/analytics/build_trades_quality_audit_v1.py \
  | tee /tmp/trades_quality_audit_v1.out

grep -q "TRADES_QUALITY_SUMMARY" /tmp/trades_quality_audit_v1.out
grep -q "TRADES_QUALITY_SOURCE" /tmp/trades_quality_audit_v1.out
grep -q "TRADES_ANALYTICS_CANDIDATE" /tmp/trades_quality_audit_v1.out
grep -q "TRADES_QUALITY_AUDIT_VERDICT" /tmp/trades_quality_audit_v1.out
grep -q "TRADES_QUALITY_AUDIT_V1_OK" /tmp/trades_quality_audit_v1.out

echo "TEST_TRADES_QUALITY_AUDIT_V1_OK"
