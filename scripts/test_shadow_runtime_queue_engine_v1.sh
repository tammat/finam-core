#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_QUEUE_ENGINE_V1 ==="

src/scripts/research/build_shadow_runtime_queue_engine_v1.py \
  --save \
  | tee /tmp/shadow_runtime_queue_engine_v1.out

grep -q "SHADOW_RUNTIME_QUEUE_ENGINE_V1" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "mode=save" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "rows_total=1" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "ready_rows=1" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "duplicate_candidates=0" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "queue=MSC-000001" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "status=READY" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "reason=PASS_TO_SHADOW" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "runtime_changed=0" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "execution_changed=0" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/shadow_runtime_queue_engine_v1.out
grep -q "VERDICT=SHADOW_RUNTIME_QUEUE_ENGINE_V1_READY" /tmp/shadow_runtime_queue_engine_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'table_exists=' || EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='research'
      AND table_name='shadow_runtime_queue_v1'
);

SELECT 'queue_rows=' || count(*)
FROM research.shadow_runtime_queue_v1;

SELECT 'ready_rows=' || count(*)
FROM research.shadow_runtime_queue_v1
WHERE queue_status='READY';

SELECT 'latest_queue=' ||
       candidate_id || '|' ||
       symbol || '|' ||
       strategy || '|' ||
       timeframe || '|' ||
       queue_status || '|' ||
       queue_reason
FROM research.shadow_runtime_queue_v1
ORDER BY updated_at DESC
LIMIT 1;
SQL

echo "TEST_SHADOW_RUNTIME_QUEUE_ENGINE_V1_OK"
