#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_SOURCE_REGISTRY_DB_VALIDATION_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/validate_data_source_registry_v1.py \
  >/tmp/data_source_registry_db_validation_v1.out

cat /tmp/data_source_registry_db_validation_v1.out

grep -q "VERDICT=DATA_SOURCE_REGISTRY_DB_VALIDATION_V1_READY" /tmp/data_source_registry_db_validation_v1.out
grep -q "active_sources=12" /tmp/data_source_registry_db_validation_v1.out
grep -q "missing_sources=0" /tmp/data_source_registry_db_validation_v1.out
grep -q "missing_domains=0" /tmp/data_source_registry_db_validation_v1.out
grep -q "duplicate_sources=0" /tmp/data_source_registry_db_validation_v1.out
grep -q "ai_gated_rows=1" /tmp/data_source_registry_db_validation_v1.out
grep -q "runtime_live_block_rows=1" /tmp/data_source_registry_db_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/data_source_registry_db_validation_v1.out

echo "registry_validation=READY"
echo "required_sources=READY"
echo "required_domains=READY"
echo "uniqueness=READY"
echo "ai_order_access=BLOCKED"
echo "runtime_trading=BLOCKED_FOR_LIVE"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_SOURCE_REGISTRY_DB_VALIDATION_V1_OK"
