#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_runtime_gold_watch_mode_v1.py

python3 src/scripts/runtime/build_runtime_gold_watch_mode_v1.py \
  | tee /tmp/runtime_gold_watch_mode_v1.log

grep -q "RUNTIME_GOLD_WATCH_MODE_V1_OK" /tmp/runtime_gold_watch_mode_v1.log
grep -q "status=WATCH_RUNTIME_ACTIVE" /tmp/runtime_gold_watch_mode_v1.log
grep -q "runtime_allowed=0" /tmp/runtime_gold_watch_mode_v1.log
grep -q "execution_enabled=0" /tmp/runtime_gold_watch_mode_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT symbol, status, runtime_allowed, execution_enabled, reason
FROM runtime_candidate_registry
WHERE symbol='GDU6@RTSX';
" | tee /tmp/runtime_gold_watch_mode_db_v1.log

grep -q "WATCH_RUNTIME_ACTIVE" /tmp/runtime_gold_watch_mode_db_v1.log
grep -q " f " /tmp/runtime_gold_watch_mode_db_v1.log

echo TEST_RUNTIME_GOLD_WATCH_MODE_V1_OK
