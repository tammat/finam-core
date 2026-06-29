#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_DISCOVERY_PROFILE_V1 ==="

PYTHONPATH=src src/scripts/research/build_feature_discovery_profile_v1.py \
  | tee /tmp/feature_discovery_profile_v1.out

grep -q "FEATURE_DISCOVERY_PROFILE_V1" /tmp/feature_discovery_profile_v1.out
grep -q "domain=FEATURES" /tmp/feature_discovery_profile_v1.out
grep -q "catalog_features_total=" /tmp/feature_discovery_profile_v1.out
grep -q "discovery_plugins=FeatureDiscovery" /tmp/feature_discovery_profile_v1.out
grep -q "writer=CatalogWriter" /tmp/feature_discovery_profile_v1.out
grep -q "write_policy=UPSERT_BY_OBJECT_ID" /tmp/feature_discovery_profile_v1.out
grep -q "target_catalog=warehouse.analytics_asset_catalog_v1" /tmp/feature_discovery_profile_v1.out
grep -q "runtime_changed=0" /tmp/feature_discovery_profile_v1.out
grep -q "execution_changed=0" /tmp/feature_discovery_profile_v1.out
grep -q "orders_changed=0" /tmp/feature_discovery_profile_v1.out
grep -q "fills_changed=0" /tmp/feature_discovery_profile_v1.out
grep -q "micro_live_allowed=0" /tmp/feature_discovery_profile_v1.out
grep -q "VERDICT=FEATURE_DISCOVERY_PROFILE_V1_READY" /tmp/feature_discovery_profile_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'catalog_features_rows=' || count(*)
FROM warehouse.analytics_asset_catalog_v1
WHERE domain='FEATURES';

SELECT 'catalog_features_health=' ||
       string_agg(health_light || ':' || cnt, ',' ORDER BY health_light)
FROM (
    SELECT health_light, count(*) AS cnt
    FROM warehouse.analytics_asset_catalog_v1
    WHERE domain='FEATURES'
    GROUP BY health_light
) s;
SQL

echo "TEST_FEATURE_DISCOVERY_PROFILE_V1_OK"
