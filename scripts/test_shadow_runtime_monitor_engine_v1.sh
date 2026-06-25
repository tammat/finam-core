#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_MONITOR_ENGINE_V1 ==="

src/scripts/research/build_shadow_runtime_monitor_engine_v1.py --save \
  | tee /tmp/shadow_runtime_monitor_engine_v1.out

grep -q "SHADOW_RUNTIME_MONITOR_ENGINE_V1" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "mode=save" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "planned_to_starting_rows=1" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "monitor=MSC-000001" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "PLANNED->STARTING" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "runtime_changed=0" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "execution_changed=0" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "orders_changed=0" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "fills_changed=0" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/shadow_runtime_monitor_engine_v1.out
grep -q "VERDICT=SHADOW_RUNTIME_MONITOR_ENGINE_V1_READY" /tmp/shadow_runtime_monitor_engine_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'table_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='shadow_runtime_monitor_v1'
);

SELECT 'monitor_rows=' || count(*)
FROM research.shadow_runtime_monitor_v1;

SELECT 'planned_to_starting=' || count(*)
FROM research.shadow_runtime_monitor_v1
WHERE transition_from='PLANNED'
  AND transition_to='STARTING';

SELECT 'latest_monitor=' ||
       candidate_id || '|' ||
       symbol || '|' ||
       strategy || '|' ||
       timeframe || '|' ||
       transition_from || '->' ||
       transition_to
FROM research.shadow_runtime_monitor_v1
ORDER BY event_ts DESC, monitor_id DESC
LIMIT 1;
SQL

echo "TEST_SHADOW_RUNTIME_MONITOR_ENGINE_V1_OK"
