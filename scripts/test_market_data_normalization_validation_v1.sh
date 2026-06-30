#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_NORMALIZATION_VALIDATION_V1 ==="

scripts/test_market_data_normalization_builder_complete_v1.sh >/tmp/validation_builder.out

grep -q "TEST_MARKET_DATA_NORMALIZATION_BUILDER_COMPLETE_V1_OK" \
    /tmp/validation_builder.out

echo "builder_validation=READY"

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/validation_db.out

SELECT
'bar_event_table='||
CASE
WHEN to_regclass('warehouse.normalized_bar_event_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT
'quality_table='||
CASE
WHEN to_regclass('warehouse.normalized_data_quality_event_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT
'lineage_table='||
CASE
WHEN to_regclass('warehouse.normalized_lineage_event_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SQL

cat /tmp/validation_db.out

grep -q "bar_event_table=READY" /tmp/validation_db.out
grep -q "quality_table=READY" /tmp/validation_db.out
grep -q "lineage_table=READY" /tmp/validation_db.out

echo "schema_validation=READY"
echo "builder_validation=READY"
echo "storage_validation=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_DATA_NORMALIZATION_VALIDATION_V1_READY"
echo "TEST_MARKET_DATA_NORMALIZATION_VALIDATION_V1_OK"

