#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_runtime_candidate_scorecard_v1.py

python3 src/scripts/runtime/build_runtime_candidate_scorecard_v1.py \
  | tee /tmp/runtime_candidate_scorecard_v1.log

grep -q "RUNTIME CANDIDATE SCORECARD V1" /tmp/runtime_candidate_scorecard_v1.log
grep -q "SCORECARD_ROW symbol=GDU6@RTSX" /tmp/runtime_candidate_scorecard_v1.log
grep -q "source=GOLD_SHADOW_FILTERED" /tmp/runtime_candidate_scorecard_v1.log
grep -q "review_gate=READY_FOR_RUNTIME_REVIEW" /tmp/runtime_candidate_scorecard_v1.log
grep -q "runtime_allow=0" /tmp/runtime_candidate_scorecard_v1.log
grep -q "execution_enabled=0" /tmp/runtime_candidate_scorecard_v1.log
grep -q "RUNTIME_CANDIDATE_SCORECARD_V1_OK" /tmp/runtime_candidate_scorecard_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    status,
    source,
    trades,
    expectancy,
    profit_factor,
    stability_ratio,
    review_gate,
    runtime_allowed,
    execution_enabled
FROM runtime_candidate_scorecard
ORDER BY id DESC
LIMIT 5;
" | tee /tmp/runtime_candidate_scorecard_db_v1.log

grep -q "GDU6@RTSX" /tmp/runtime_candidate_scorecard_db_v1.log
grep -q "GOLD_SHADOW_FILTERED" /tmp/runtime_candidate_scorecard_db_v1.log
grep -q " f " /tmp/runtime_candidate_scorecard_db_v1.log

echo TEST_RUNTIME_CANDIDATE_SCORECARD_V1_OK
