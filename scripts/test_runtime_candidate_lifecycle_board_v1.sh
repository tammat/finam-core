#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_runtime_candidate_lifecycle_board_v1.py

python3 src/scripts/runtime/build_runtime_candidate_lifecycle_board_v1.py \
  | tee /tmp/runtime_candidate_lifecycle_board_v1.log

grep -q "RUNTIME CANDIDATE LIFECYCLE BOARD V1" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "symbol=GDU6@RTSX" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "symbol=LKOH@MISX" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "symbol=USDRUBF@RTSX" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "symbol=BRN6@RTSX" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "symbol=NGN6@RTSX" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "event_type=REGISTRY" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "event_type=DECISION" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "READY_FOR_RUNTIME_REVIEW" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "PROMOTE_RUNTIME_REVIEW" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "runtime_allow=0" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "execution_enabled=0" /tmp/runtime_candidate_lifecycle_board_v1.log
grep -q "RUNTIME_CANDIDATE_LIFECYCLE_BOARD_V1_OK" /tmp/runtime_candidate_lifecycle_board_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    event_type,
    event_status,
    runtime_allowed,
    execution_enabled
FROM runtime_candidate_lifecycle_board
ORDER BY id DESC
LIMIT 10;
" | tee /tmp/runtime_candidate_lifecycle_board_db_v1.log

grep -q "GDU6@RTSX" /tmp/runtime_candidate_lifecycle_board_db_v1.log
grep -q "PROMOTE_RUNTIME_REVIEW" /tmp/runtime_candidate_lifecycle_board_db_v1.log
grep -q " f " /tmp/runtime_candidate_lifecycle_board_db_v1.log

echo TEST_RUNTIME_CANDIDATE_LIFECYCLE_BOARD_V1_OK
