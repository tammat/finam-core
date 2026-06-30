#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_STRATEGY_CLASS_DISCOVERY_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_strategy_class_discovery_audit_v1.py

src/scripts/research/build_strategy_class_discovery_audit_v1.py \
  | tee /tmp/strategy_class_discovery_audit_v1.out

grep -q "CLASS_RANKING" /tmp/strategy_class_discovery_audit_v1.out
grep -q "CLASS_ROW strategy_class=" /tmp/strategy_class_discovery_audit_v1.out
grep -q "best_class=" /tmp/strategy_class_discovery_audit_v1.out
grep -q "worst_class=" /tmp/strategy_class_discovery_audit_v1.out
grep -q "VERDICT=STRATEGY_CLASS_DISCOVERY_AUDIT_READY" /tmp/strategy_class_discovery_audit_v1.out

echo "TEST_STRATEGY_CLASS_DISCOVERY_AUDIT_V1_OK"
