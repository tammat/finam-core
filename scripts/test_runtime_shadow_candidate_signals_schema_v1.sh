#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_shadow_candidate_signals_schema_v1.py

python3 \
  src/scripts/analytics/build_runtime_shadow_candidate_signals_schema_v1.py \
  | tee /tmp/runtime_shadow_candidate_signals_schema_v1.log

grep -q "RUNTIME SHADOW CANDIDATE SIGNALS SCHEMA V1" \
  /tmp/runtime_shadow_candidate_signals_schema_v1.log

grep -q "runtime_allow_default=0" \
  /tmp/runtime_shadow_candidate_signals_schema_v1.log

grep -q "execution_enabled_default=0" \
  /tmp/runtime_shadow_candidate_signals_schema_v1.log

grep -q "RUNTIME_SHADOW_CANDIDATE_SIGNALS_SCHEMA_V1_OK" \
  /tmp/runtime_shadow_candidate_signals_schema_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
  table_name,
  column_name
FROM information_schema.columns
WHERE table_schema='public'
  AND table_name='runtime_shadow_candidate_signals_v1'
ORDER BY ordinal_position;
"

echo TEST_RUNTIME_SHADOW_CANDIDATE_SIGNALS_SCHEMA_V1_OK
