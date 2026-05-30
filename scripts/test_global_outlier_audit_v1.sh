#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_GLOBAL_OUTLIER_AUDIT_V1_START"

python -m py_compile src/scripts/analytics/build_global_outlier_audit_v1.py

python src/scripts/analytics/build_global_outlier_audit_v1.py \
  --window-days 365 \
  --outlier-pct 0.20 \
  --min-trades 20 \
  --limit-symbols 50 \
  --limit-trades 100 | tee /tmp/global_outlier_audit_v1.out

grep -q "GLOBAL_OUTLIER_AUDIT_V1" /tmp/global_outlier_audit_v1.out
grep -q "GLOBAL_OUTLIER_VERDICT" /tmp/global_outlier_audit_v1.out
grep -q "GLOBAL_OUTLIER_AUDIT_V1_OK" /tmp/global_outlier_audit_v1.out

echo "TEST_GLOBAL_OUTLIER_AUDIT_V1_OK"
