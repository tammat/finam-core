#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_CATALOG_DISCOVERY_VALIDATION_V1 ==="

PYTHONPATH=src src/scripts/research/build_catalog_discovery_validation_v1.py \
  | tee /tmp/catalog_discovery_validation_v1.out

grep -q "CATALOG_DISCOVERY_VALIDATION_V1" /tmp/catalog_discovery_validation_v1.out
grep -q "domain=WORKFLOW" /tmp/catalog_discovery_validation_v1.out
grep -q "catalog_total=37" /tmp/catalog_discovery_validation_v1.out
grep -q "required_fields_valid=37" /tmp/catalog_discovery_validation_v1.out
grep -q "duplicate_object_ids=0" /tmp/catalog_discovery_validation_v1.out
grep -q "green_objects=37" /tmp/catalog_discovery_validation_v1.out
grep -q "source_count=PostgresDiscovery:16" /tmp/catalog_discovery_validation_v1.out
grep -q "source_count=PythonDiscovery:" /tmp/catalog_discovery_validation_v1.out
grep -q "validation_policy=REQUIRED_FIELDS_NO_DUPLICATES_GREEN_HEALTH" /tmp/catalog_discovery_validation_v1.out
grep -q "workflow_profile_valid=1" /tmp/catalog_discovery_validation_v1.out
grep -q "runtime_changed=0" /tmp/catalog_discovery_validation_v1.out
grep -q "execution_changed=0" /tmp/catalog_discovery_validation_v1.out
grep -q "orders_changed=0" /tmp/catalog_discovery_validation_v1.out
grep -q "fills_changed=0" /tmp/catalog_discovery_validation_v1.out
grep -q "micro_live_allowed=0" /tmp/catalog_discovery_validation_v1.out
grep -q "VERDICT=CATALOG_DISCOVERY_VALIDATION_V1_READY" /tmp/catalog_discovery_validation_v1.out

echo "TEST_CATALOG_DISCOVERY_VALIDATION_V1_OK"
