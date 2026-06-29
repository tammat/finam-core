#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MODEL_DISCOVERY_PROFILE_V1 ==="

PYTHONPATH=src src/scripts/research/build_model_discovery_profile_v1.py \
  | tee /tmp/model_discovery_profile_v1.out

grep -q "MODEL_DISCOVERY_PROFILE_V1" /tmp/model_discovery_profile_v1.out
grep -q "domain=MODELS" /tmp/model_discovery_profile_v1.out
grep -q "catalog_models_total=" /tmp/model_discovery_profile_v1.out
grep -q "discovery_plugins=ModelDiscovery" /tmp/model_discovery_profile_v1.out
grep -q "writer=CatalogWriter" /tmp/model_discovery_profile_v1.out
grep -q "write_policy=UPSERT_BY_OBJECT_ID" /tmp/model_discovery_profile_v1.out
grep -q "target_catalog=warehouse.analytics_asset_catalog_v1" /tmp/model_discovery_profile_v1.out
grep -q "runtime_changed=0" /tmp/model_discovery_profile_v1.out
grep -q "execution_changed=0" /tmp/model_discovery_profile_v1.out
grep -q "orders_changed=0" /tmp/model_discovery_profile_v1.out
grep -q "fills_changed=0" /tmp/model_discovery_profile_v1.out
grep -q "micro_live_allowed=0" /tmp/model_discovery_profile_v1.out
grep -q "VERDICT=MODEL_DISCOVERY_PROFILE_V1_READY" /tmp/model_discovery_profile_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'catalog_models_rows=' || count(*)
FROM warehouse.analytics_asset_catalog_v1
WHERE domain='MODELS';

SELECT 'catalog_models_health=' ||
       string_agg(health_light || ':' || cnt, ',' ORDER BY health_light)
FROM (
    SELECT health_light, count(*) AS cnt
    FROM warehouse.analytics_asset_catalog_v1
    WHERE domain='MODELS'
    GROUP BY health_light
) s;
SQL

echo "TEST_MODEL_DISCOVERY_PROFILE_V1_OK"
