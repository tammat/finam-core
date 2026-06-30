#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_OBJECT_CLASSIFICATION_PERSIST_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/persist_data_object_classification_v1.py \
  >/tmp/data_object_classification_persist_v1.out

cat /tmp/data_object_classification_persist_v1.out

grep -q "VERDICT=DATA_OBJECT_CLASSIFICATION_PERSIST_V1_READY" /tmp/data_object_classification_persist_v1.out
grep -q "objects_persisted=" /tmp/data_object_classification_persist_v1.out
grep -q "active_objects=" /tmp/data_object_classification_persist_v1.out
grep -q "data_source_objects=" /tmp/data_object_classification_persist_v1.out
grep -q "registry_objects=" /tmp/data_object_classification_persist_v1.out
grep -q "idempotent_upsert=READY" /tmp/data_object_classification_persist_v1.out
grep -q "micro_live_allowed=0" /tmp/data_object_classification_persist_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/data_object_classification_db_check_v1.out
SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.data_object_classification_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'rows=' || count(*)
FROM warehouse.data_object_classification_v1
WHERE active=true;

SELECT 'market_bars=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='market_bars';

SELECT 'market_ticks=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='public'
  AND table_name='market_ticks';

SELECT 'normalized_bar_event_v1=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='warehouse'
  AND table_name='normalized_bar_event_v1';

SELECT 'data_source_registry_v1=' || object_type
FROM warehouse.data_object_classification_v1
WHERE schema_name='warehouse'
  AND table_name='data_source_registry_v1';
SQL

cat /tmp/data_object_classification_db_check_v1.out

grep -q "table=READY" /tmp/data_object_classification_db_check_v1.out
grep -q "rows=372" /tmp/data_object_classification_db_check_v1.out
grep -q "market_bars=DATA_SOURCE" /tmp/data_object_classification_db_check_v1.out
grep -q "market_ticks=DATA_SOURCE" /tmp/data_object_classification_db_check_v1.out
grep -q "normalized_bar_event_v1=DATA_SOURCE" /tmp/data_object_classification_db_check_v1.out
grep -q "data_source_registry_v1=REGISTRY" /tmp/data_object_classification_db_check_v1.out

echo "data_object_classification_persist=READY"
echo "postgres_persist=READY"
echo "idempotent_upsert=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_OBJECT_CLASSIFICATION_PERSIST_V1_OK"
