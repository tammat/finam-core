#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_STRATEGY_CLASS_DISCOVERY_AUDIT_V2 ==="

python3 -m py_compile \
  src/scripts/research/build_strategy_class_discovery_audit_v2.py

src/scripts/research/build_strategy_class_discovery_audit_v2.py \
  | tee /tmp/strategy_class_discovery_audit_v2.out

grep -q "source_table=analytics_rs_bottom_runtime_dry_run_v1" /tmp/strategy_class_discovery_audit_v2.out
grep -q "CLASS_RANKING" /tmp/strategy_class_discovery_audit_v2.out
grep -q "CLASS_ROW strategy_class=" /tmp/strategy_class_discovery_audit_v2.out
grep -q "best_class=" /tmp/strategy_class_discovery_audit_v2.out
grep -q "VERDICT=STRATEGY_CLASS_DISCOVERY_AUDIT_V2_READY" /tmp/strategy_class_discovery_audit_v2.out

echo "TEST_STRATEGY_CLASS_DISCOVERY_AUDIT_V2_OK"
