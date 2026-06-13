#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_runtime_candidate_decision_board_v1.py

python3 src/scripts/runtime/build_runtime_candidate_decision_board_v1.py \
  | tee /tmp/runtime_candidate_decision_board_v1.log

grep -q "RUNTIME CANDIDATE DECISION BOARD V1" /tmp/runtime_candidate_decision_board_v1.log
grep -q "symbol=GDU6@RTSX .*decision=PROMOTE_RUNTIME_REVIEW" /tmp/runtime_candidate_decision_board_v1.log
grep -q "symbol=LKOH@MISX .*decision=WATCH_RESEARCH" /tmp/runtime_candidate_decision_board_v1.log
grep -q "symbol=USDRUBF@RTSX .*decision=WATCH_RESEARCH" /tmp/runtime_candidate_decision_board_v1.log
grep -q "symbol=BRN6@RTSX .*decision=REJECT" /tmp/runtime_candidate_decision_board_v1.log
grep -q "symbol=NGN6@RTSX .*decision=REJECT" /tmp/runtime_candidate_decision_board_v1.log
grep -q "SUMMARY_ROW promote=1 watch=2 reject=2" /tmp/runtime_candidate_decision_board_v1.log
grep -q "runtime_allow=0" /tmp/runtime_candidate_decision_board_v1.log
grep -q "execution_enabled=0" /tmp/runtime_candidate_decision_board_v1.log
grep -q "RUNTIME_CANDIDATE_DECISION_BOARD_V1_OK" /tmp/runtime_candidate_decision_board_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    candidate_status,
    review_gate,
    decision,
    runtime_allowed,
    execution_enabled
FROM runtime_candidate_decision_board
ORDER BY id DESC
LIMIT 5;
" | tee /tmp/runtime_candidate_decision_board_db_v1.log

grep -q "GDU6@RTSX" /tmp/runtime_candidate_decision_board_db_v1.log
grep -q "PROMOTE_RUNTIME_REVIEW" /tmp/runtime_candidate_decision_board_db_v1.log
grep -q " f " /tmp/runtime_candidate_decision_board_db_v1.log

echo TEST_RUNTIME_CANDIDATE_DECISION_BOARD_V1_OK
