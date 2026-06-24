#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_STRATEGY_CLASS_DISCOVERY_SOURCE_SCHEMA_AUDIT_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_strategy_class_discovery_source_schema_audit_v1.py

src/scripts/research/build_strategy_class_discovery_source_schema_audit_v1.py \
  | tee /tmp/strategy_class_discovery_source_schema_audit_v1.out

grep -q "TABLE table=analytics_futures_rs_bottom_paper_observation_v1 exists=1" /tmp/strategy_class_discovery_source_schema_audit_v1.out
grep -q "VERDICT=STRATEGY_CLASS_DISCOVERY_SOURCE_SCHEMA_AUDIT_READY" /tmp/strategy_class_discovery_source_schema_audit_v1.out

echo "TEST_STRATEGY_CLASS_DISCOVERY_SOURCE_SCHEMA_AUDIT_V1_OK"
