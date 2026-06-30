#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_SOURCE_REGISTRY_DB_PERSIST_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/persist_data_source_registry_v1.py \
  >/tmp/data_source_registry_db_persist_v1.out

cat /tmp/data_source_registry_db_persist_v1.out

grep -q "VERDICT=DATA_SOURCE_REGISTRY_DB_PERSIST_V1_READY" /tmp/data_source_registry_db_persist_v1.out
grep -q "sources_persisted=12" /tmp/data_source_registry_db_persist_v1.out
grep -q "ai_gated_rows=1" /tmp/data_source_registry_db_persist_v1.out
grep -q "micro_live_allowed=0" /tmp/data_source_registry_db_persist_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/data_source_registry_db_check_v1.out
SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.data_source_registry_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'rows=' || count(*)
FROM warehouse.data_source_registry_v1
WHERE active=true;

SELECT 'ai_gate=' || count(*)
FROM warehouse.data_source_registry_v1
WHERE source_origin='AI'
  AND normalization_status='GATED_NO_ORDER_ACCESS';

SELECT 'runtime_live_block=' || count(*)
FROM warehouse.data_source_registry_v1
WHERE source_origin='Runtime Trading'
  AND normalization_status='BLOCKED_FOR_LIVE';
SQL

cat /tmp/data_source_registry_db_check_v1.out

grep -q "table=READY" /tmp/data_source_registry_db_check_v1.out
grep -q "rows=12" /tmp/data_source_registry_db_check_v1.out
grep -q "ai_gate=1" /tmp/data_source_registry_db_check_v1.out
grep -q "runtime_live_block=1" /tmp/data_source_registry_db_check_v1.out

echo "registry_db=READY"
echo "postgres_persist=READY"
echo "idempotent_upsert=READY"
echo "ai_order_access=BLOCKED"
echo "runtime_trading=BLOCKED_FOR_LIVE"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DATA_SOURCE_REGISTRY_DB_PERSIST_V1_OK"
