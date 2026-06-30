#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_METADATA_CLASSIFIER_VERSIONING_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/build_metadata_classifier_versioning_v1.py \
  >/tmp/metadata_classifier_versioning_v1.out

cat /tmp/metadata_classifier_versioning_v1.out

grep -q "VERDICT=METADATA_CLASSIFIER_VERSIONING_V1_READY" /tmp/metadata_classifier_versioning_v1.out
grep -q "metadata_version=1.0.0" /tmp/metadata_classifier_versioning_v1.out
grep -q "classifier_version=1.0.0" /tmp/metadata_classifier_versioning_v1.out
grep -q "registry_version=1.0.0" /tmp/metadata_classifier_versioning_v1.out
grep -q "normalization_version=1.0.0" /tmp/metadata_classifier_versioning_v1.out
grep -q "sources_total=12" /tmp/metadata_classifier_versioning_v1.out
grep -q "objects_total=373" /tmp/metadata_classifier_versioning_v1.out
grep -q "data_source_objects=33" /tmp/metadata_classifier_versioning_v1.out
grep -q "coverage_pct=100.0" /tmp/metadata_classifier_versioning_v1.out
grep -q "other_objects=10" /tmp/metadata_classifier_versioning_v1.out
grep -q "validation_status=PASSED" /tmp/metadata_classifier_versioning_v1.out
grep -q "release_status=RELEASED" /tmp/metadata_classifier_versioning_v1.out
grep -q "runtime_changed=0" /tmp/metadata_classifier_versioning_v1.out
grep -q "micro_live_allowed=0" /tmp/metadata_classifier_versioning_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/metadata_classifier_versioning_db_check_v1.out
SELECT 'release_table=' ||
CASE WHEN to_regclass('warehouse.metadata_release_registry_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'component_table=' ||
CASE WHEN to_regclass('warehouse.metadata_component_registry_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'validation_table=' ||
CASE WHEN to_regclass('warehouse.metadata_validation_snapshot_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'release=' || status
FROM warehouse.metadata_release_registry_v1
WHERE metadata_version='1.0.0';

SELECT 'components=' || count(*)
FROM warehouse.metadata_component_registry_v1
WHERE metadata_version='1.0.0'
  AND active=true;

SELECT 'validation=' || validation_status
FROM warehouse.metadata_validation_snapshot_v1
WHERE metadata_version='1.0.0';

SELECT 'coverage=' || coverage_pct
FROM warehouse.metadata_validation_snapshot_v1
WHERE metadata_version='1.0.0';

SELECT 'other=' || other_objects
FROM warehouse.metadata_validation_snapshot_v1
WHERE metadata_version='1.0.0';
SQL

cat /tmp/metadata_classifier_versioning_db_check_v1.out

grep -q "release_table=READY" /tmp/metadata_classifier_versioning_db_check_v1.out
grep -q "component_table=READY" /tmp/metadata_classifier_versioning_db_check_v1.out
grep -q "validation_table=READY" /tmp/metadata_classifier_versioning_db_check_v1.out
grep -q "release=RELEASED" /tmp/metadata_classifier_versioning_db_check_v1.out
grep -q "components=7" /tmp/metadata_classifier_versioning_db_check_v1.out
grep -q "validation=PASSED" /tmp/metadata_classifier_versioning_db_check_v1.out
grep -q "coverage=100.0" /tmp/metadata_classifier_versioning_db_check_v1.out
grep -q "other=10" /tmp/metadata_classifier_versioning_db_check_v1.out

echo "metadata_versioning=READY"
echo "release_registry=READY"
echo "component_registry=READY"
echo "validation_snapshot=READY"
echo "metadata_catalog_v1_0_0=RELEASED"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_METADATA_CLASSIFIER_VERSIONING_V1_OK"
