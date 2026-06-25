#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SHADOW_RUNTIME_ENGINE_V1 ==="

src/scripts/research/build_shadow_runtime_engine_v1.py --save \
  | tee /tmp/shadow_runtime_engine_v1.out

grep -q "SHADOW_RUNTIME_ENGINE_V1" /tmp/shadow_runtime_engine_v1.out
grep -q "mode=save" /tmp/shadow_runtime_engine_v1.out
grep -q "rows_total=1" /tmp/shadow_runtime_engine_v1.out
grep -q "planned_rows=1" /tmp/shadow_runtime_engine_v1.out
grep -q "run=MSC-000001" /tmp/shadow_runtime_engine_v1.out
grep -q "runtime_changed=0" /tmp/shadow_runtime_engine_v1.out
grep -q "execution_changed=0" /tmp/shadow_runtime_engine_v1.out
grep -q "orders_changed=0" /tmp/shadow_runtime_engine_v1.out
grep -q "fills_changed=0" /tmp/shadow_runtime_engine_v1.out
grep -q "micro_live_allowed=0" /tmp/shadow_runtime_engine_v1.out
grep -q "VERDICT=SHADOW_RUNTIME_ENGINE_V1_READY" /tmp/shadow_runtime_engine_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
SELECT 'run_rows=' || count(*)
FROM research.shadow_runtime_runs_v1;

SELECT 'planned=' || count(*)
FROM research.shadow_runtime_runs_v1
WHERE run_status='PLANNED';
SQL

echo "TEST_SHADOW_RUNTIME_ENGINE_V1_OK"
