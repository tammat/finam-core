#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_CATALOG_WRITER_V1 ==="

PYTHONPATH=src src/scripts/research/build_catalog_writer_v1.py \
  | tee /tmp/catalog_writer_v1.out

grep -q "CATALOG_WRITER_V1" /tmp/catalog_writer_v1.out
grep -q "profile=WORKFLOW_DISCOVERY_PROFILE_V1" /tmp/catalog_writer_v1.out
grep -q "catalog_object=postgres:warehouse.qlt_workflow_event_v1" /tmp/catalog_writer_v1.out
grep -q "catalog_object=postgres:warehouse.nrm_workflow_event_v1" /tmp/catalog_writer_v1.out
grep -q "catalog_object=postgres:warehouse.fact_event_workflow_stage_v1" /tmp/catalog_writer_v1.out
grep -q "catalog_object=postgres:warehouse.fact_state_candidate_lifecycle_v1" /tmp/catalog_writer_v1.out
grep -q "catalog_object=postgres:warehouse.sem_candidate_v1" /tmp/catalog_writer_v1.out
grep -q "catalog_object=postgres:warehouse.mart_candidate_workflow_v1" /tmp/catalog_writer_v1.out
grep -q "catalog_object=postgres:warehouse.snap_workflow_daily_v1" /tmp/catalog_writer_v1.out
grep -q "write_policy=UPSERT_BY_OBJECT_ID" /tmp/catalog_writer_v1.out
grep -q "target_catalog=warehouse.analytics_asset_catalog_v1" /tmp/catalog_writer_v1.out
grep -q "runtime_changed=0" /tmp/catalog_writer_v1.out
grep -q "execution_changed=0" /tmp/catalog_writer_v1.out
grep -q "orders_changed=0" /tmp/catalog_writer_v1.out
grep -q "fills_changed=0" /tmp/catalog_writer_v1.out
grep -q "micro_live_allowed=0" /tmp/catalog_writer_v1.out
grep -q "VERDICT=CATALOG_WRITER_V1_READY" /tmp/catalog_writer_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'catalog_workflow_rows=' || count(*)
FROM warehouse.analytics_asset_catalog_v1
WHERE domain='WORKFLOW';

SELECT 'catalog_health=' ||
       string_agg(health_light || ':' || count_health, ',' ORDER BY health_light)
FROM (
    SELECT health_light, count(*) AS count_health
    FROM warehouse.analytics_asset_catalog_v1
    WHERE domain='WORKFLOW'
    GROUP BY health_light
) s;
SQL

echo "TEST_CATALOG_WRITER_V1_OK"
