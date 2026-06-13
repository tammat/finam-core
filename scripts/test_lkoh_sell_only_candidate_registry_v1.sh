#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/runtime/build_lkoh_sell_only_candidate_registry_v1.py

python3 src/scripts/runtime/build_lkoh_sell_only_candidate_registry_v1.py \
  | tee /tmp/lkoh_sell_only_candidate_registry_v1.log

grep -q "LKOH SELL ONLY CANDIDATE REGISTRY V1" \
  /tmp/lkoh_sell_only_candidate_registry_v1.log

grep -q "status=READY_FOR_RUNTIME_REVIEW" \
  /tmp/lkoh_sell_only_candidate_registry_v1.log

grep -q "source=lkoh_sell_only_scorecard_v1" \
  /tmp/lkoh_sell_only_candidate_registry_v1.log

grep -q "runtime_allowed=0" \
  /tmp/lkoh_sell_only_candidate_registry_v1.log

grep -q "execution_enabled=0" \
  /tmp/lkoh_sell_only_candidate_registry_v1.log

grep -q "LKOH_SELL_ONLY_CANDIDATE_REGISTRY_V1_OK" \
  /tmp/lkoh_sell_only_candidate_registry_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    status,
    reason,
    source,
    runtime_allowed,
    execution_enabled
FROM runtime_candidate_registry
WHERE symbol='LKOH@MISX';
" | tee /tmp/lkoh_registry_db_v1.log

grep -q "LKOH@MISX" /tmp/lkoh_registry_db_v1.log
grep -q "READY_FOR_RUNTIME_REVIEW" /tmp/lkoh_registry_db_v1.log
grep -q "lkoh_sell_only_scorecard_v1" /tmp/lkoh_registry_db_v1.log
grep -q " f " /tmp/lkoh_registry_db_v1.log

echo TEST_LKOH_SELL_ONLY_CANDIDATE_REGISTRY_V1_OK
