#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL CLASS NORMALIZATION AUDIT V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_signal_class_normalization_audit_v1.py

PYTHONPATH=src python3 src/scripts/research/build_signal_class_normalization_audit_v1.py \
  | tee /tmp/signal_class_normalization_audit_v1.log

grep -q "SIGNAL_CLASS_NORMALIZATION_AUDIT_V1_OK" /tmp/signal_class_normalization_audit_v1.log
grep -q "SIGNAL_CLASS_NORMALIZATION_AUDIT_SUMMARY" /tmp/signal_class_normalization_audit_v1.log
grep -q "trades_total=" /tmp/signal_class_normalization_audit_v1.log
grep -q "normalized_classes=" /tmp/signal_class_normalization_audit_v1.log
grep -q "dynamic_reason_rows=" /tmp/signal_class_normalization_audit_v1.log
grep -q "recommended_normalize_reason=1" /tmp/signal_class_normalization_audit_v1.log
grep -q "VERDICT=" /tmp/signal_class_normalization_audit_v1.log
grep -q "db_update=0" /tmp/signal_class_normalization_audit_v1.log

echo
echo "=== SIGNAL CLASS NORMALIZATION SUMMARY ==="
grep -E "SIGNAL_CLASS_NORMALIZATION_ROW|trades_total=|normalized_classes=|dynamic_reason_rows=|unknown_source_rows=|unknown_regime_rows=|VERDICT=" \
  /tmp/signal_class_normalization_audit_v1.log | head -80

echo TEST_SIGNAL_CLASS_NORMALIZATION_AUDIT_V1_OK
