#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_runtime_shadow_candidate_collector_v1.py

python3 \
  src/scripts/analytics/build_runtime_shadow_candidate_collector_v1.py \
  | tee /tmp/runtime_shadow_candidate_collector_v1.log

grep -q "RUNTIME SHADOW CANDIDATE COLLECTOR V1" \
  /tmp/runtime_shadow_candidate_collector_v1.log

grep -q "runtime_changed=0" \
  /tmp/runtime_shadow_candidate_collector_v1.log

grep -q "execution=disabled" \
  /tmp/runtime_shadow_candidate_collector_v1.log

grep -q "SUMMARY_ROW" \
  /tmp/runtime_shadow_candidate_collector_v1.log

grep -q "RUNTIME_SHADOW_CANDIDATE_COLLECTOR_V1_OK" \
  /tmp/runtime_shadow_candidate_collector_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
  source,
  COUNT(*) rows,
  COUNT(*) FILTER (WHERE runtime_allow=1) runtime_allow_rows,
  COUNT(*) FILTER (WHERE execution_enabled=1) execution_enabled_rows
FROM runtime_shadow_candidate_signals_v1
WHERE source='runtime_shadow_candidate_collector_v1'
GROUP BY source;
"

echo TEST_RUNTIME_SHADOW_CANDIDATE_COLLECTOR_V1_OK
