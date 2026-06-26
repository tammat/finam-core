#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKFLOW_DISCOVERY_PROFILE_V1_1 ==="

PYTHONPATH=src src/scripts/research/build_workflow_discovery_profile_v1.py \
  | tee /tmp/workflow_discovery_profile_v1_1.out

grep -q "WORKFLOW_DISCOVERY_PROFILE_V1_1" /tmp/workflow_discovery_profile_v1_1.out
grep -q "domain=WORKFLOW" /tmp/workflow_discovery_profile_v1_1.out
grep -q "catalog_source=PostgresDiscovery:" /tmp/workflow_discovery_profile_v1_1.out
grep -q "catalog_source=PythonDiscovery:" /tmp/workflow_discovery_profile_v1_1.out
grep -q "catalog_source=BashDiscovery:" /tmp/workflow_discovery_profile_v1_1.out
grep -q "catalog_category=TABLE:" /tmp/workflow_discovery_profile_v1_1.out
grep -q "catalog_category=SCRIPT:" /tmp/workflow_discovery_profile_v1_1.out
grep -q "discovery_plugins=PostgresDiscovery,PythonDiscovery,BashDiscovery" /tmp/workflow_discovery_profile_v1_1.out
grep -q "writer=CatalogWriter" /tmp/workflow_discovery_profile_v1_1.out
grep -q "write_policy=UPSERT_BY_OBJECT_ID" /tmp/workflow_discovery_profile_v1_1.out
grep -q "target_catalog=warehouse.analytics_asset_catalog_v1" /tmp/workflow_discovery_profile_v1_1.out
grep -q "runtime_changed=0" /tmp/workflow_discovery_profile_v1_1.out
grep -q "execution_changed=0" /tmp/workflow_discovery_profile_v1_1.out
grep -q "orders_changed=0" /tmp/workflow_discovery_profile_v1_1.out
grep -q "fills_changed=0" /tmp/workflow_discovery_profile_v1_1.out
grep -q "micro_live_allowed=0" /tmp/workflow_discovery_profile_v1_1.out
grep -q "VERDICT=WORKFLOW_DISCOVERY_PROFILE_V1_1_READY" /tmp/workflow_discovery_profile_v1_1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'workflow_catalog_rows=' || count(*)
FROM warehouse.analytics_asset_catalog_v1
WHERE domain='WORKFLOW';

SELECT 'workflow_catalog_sources=' ||
       string_agg(source || ':' || cnt, ',' ORDER BY source)
FROM (
    SELECT payload->>'discovery_source' AS source, count(*) AS cnt
    FROM warehouse.analytics_asset_catalog_v1
    WHERE domain='WORKFLOW'
    GROUP BY payload->>'discovery_source'
) s;

SELECT 'workflow_catalog_health=' ||
       string_agg(health_light || ':' || cnt, ',' ORDER BY health_light)
FROM (
    SELECT health_light, count(*) AS cnt
    FROM warehouse.analytics_asset_catalog_v1
    WHERE domain='WORKFLOW'
    GROUP BY health_light
) s;
SQL

echo "TEST_WORKFLOW_DISCOVERY_PROFILE_V1_1_OK"
