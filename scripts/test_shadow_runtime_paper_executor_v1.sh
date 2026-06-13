#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_paper_executor_v1.py

python3 src/scripts/runtime/build_shadow_runtime_paper_executor_v1.py \
  | tee /tmp/shadow_runtime_paper_executor_v1.log

grep -q "SHADOW RUNTIME PAPER EXECUTOR V1" /tmp/shadow_runtime_paper_executor_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_paper_executor_v1.log
grep -q "GDU6@RTSX" /tmp/shadow_runtime_paper_executor_v1.log
grep -q "status=ACTIVE" /tmp/shadow_runtime_paper_executor_v1.log
grep -q "status=SKIP_STALE_SOURCE" /tmp/shadow_runtime_paper_executor_v1.log
grep -q "runtime_allow=0" /tmp/shadow_runtime_paper_executor_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_paper_executor_v1.log
grep -q "SHADOW_RUNTIME_PAPER_EXECUTOR_V1_OK" /tmp/shadow_runtime_paper_executor_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    COUNT(*) AS orders,
    bool_or(execution_enabled) AS any_execution_enabled
FROM shadow_runtime_orders
GROUP BY symbol
ORDER BY symbol;
"

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    COUNT(*) AS fills,
    bool_or(execution_enabled) AS any_execution_enabled
FROM shadow_runtime_fills
GROUP BY symbol
ORDER BY symbol;
"

echo TEST_SHADOW_RUNTIME_PAPER_EXECUTOR_V1_OK
