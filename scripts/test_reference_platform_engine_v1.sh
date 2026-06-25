#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REFERENCE_PLATFORM_ENGINE_V1 ==="

PYTHONPATH=src src/scripts/research/build_reference_platform_engine_v1.py --save \
  | tee /tmp/reference_platform_engine_v1.out

grep -q "REFERENCE_PLATFORM_ENGINE_V1" /tmp/reference_platform_engine_v1.out
grep -q "mode=save" /tmp/reference_platform_engine_v1.out
grep -q "status_lights_v1=7" /tmp/reference_platform_engine_v1.out
grep -q "brokers_v1=1" /tmp/reference_platform_engine_v1.out
grep -q "exchanges_v1=1" /tmp/reference_platform_engine_v1.out
grep -q "markets_v1=3" /tmp/reference_platform_engine_v1.out
grep -q "workflow_stages_v1=8" /tmp/reference_platform_engine_v1.out
grep -q "multilingual_ready=1" /tmp/reference_platform_engine_v1.out
grep -q "traffic_lights_ready=1" /tmp/reference_platform_engine_v1.out
grep -q "ui_reference_ready=1" /tmp/reference_platform_engine_v1.out
grep -q "facts_store_codes_only=1" /tmp/reference_platform_engine_v1.out
grep -q "runtime_changed=0" /tmp/reference_platform_engine_v1.out
grep -q "execution_changed=0" /tmp/reference_platform_engine_v1.out
grep -q "orders_changed=0" /tmp/reference_platform_engine_v1.out
grep -q "fills_changed=0" /tmp/reference_platform_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/reference_platform_engine_v1.out
grep -q "VERDICT=REFERENCE_PLATFORM_ENGINE_V1_READY" /tmp/reference_platform_engine_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'lights=' || string_agg(light_code, ',' ORDER BY priority)
FROM reference.status_lights_v1;

SELECT 'ru_order_intent=' || label
FROM reference.localization_labels_v1
WHERE entity_type='workflow_stage'
  AND entity_code='ORDER_INTENT'
  AND locale_code='ru_RU';

SELECT 'ui_approval_actions=' || count(*)
FROM reference.ui_actions_v1
WHERE requires_approval=true;
SQL

echo "TEST_REFERENCE_PLATFORM_ENGINE_V1_OK"
