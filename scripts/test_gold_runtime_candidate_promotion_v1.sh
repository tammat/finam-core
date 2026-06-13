#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_gold_runtime_candidate_promotion_v1.py

python3 src/scripts/runtime/build_gold_runtime_candidate_promotion_v1.py \
  | tee /tmp/gold_runtime_candidate_promotion_v1.log

grep -q "GOLD_RUNTIME_CANDIDATE_PROMOTION_V1_OK" /tmp/gold_runtime_candidate_promotion_v1.log
grep -q "status=READY_FOR_RUNTIME_REVIEW" /tmp/gold_runtime_candidate_promotion_v1.log
grep -q "runtime_allowed=0" /tmp/gold_runtime_candidate_promotion_v1.log
grep -q "execution_enabled=0" /tmp/gold_runtime_candidate_promotion_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    status,
    reason,
    runtime_allowed,
    execution_enabled
FROM runtime_candidate_registry
WHERE symbol='GDU6@RTSX';
" | tee /tmp/gold_runtime_candidate_promotion_db_v1.log

grep -q "READY_FOR_RUNTIME_REVIEW" /tmp/gold_runtime_candidate_promotion_db_v1.log
grep -q " f " /tmp/gold_runtime_candidate_promotion_db_v1.log

echo TEST_GOLD_RUNTIME_CANDIDATE_PROMOTION_V1_OK
