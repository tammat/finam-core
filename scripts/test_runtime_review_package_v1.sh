#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_runtime_review_package_v1.py

python3 src/scripts/runtime/build_runtime_review_package_v1.py \
  | tee /tmp/runtime_review_package_v1.log

grep -q "RUNTIME REVIEW PACKAGE V1" /tmp/runtime_review_package_v1.log
grep -q "GDU6@RTSX" /tmp/runtime_review_package_v1.log
grep -q "LKOH@MISX" /tmp/runtime_review_package_v1.log
grep -q "READY_FOR_SHADOW_RUNTIME" /tmp/runtime_review_package_v1.log
grep -q "runtime_allow=0" /tmp/runtime_review_package_v1.log
grep -q "execution_enabled=0" /tmp/runtime_review_package_v1.log
grep -q "RUNTIME_REVIEW_PACKAGE_V1_OK" /tmp/runtime_review_package_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    source,
    candidate_status,
    decision_status,
    closed_trades,
    expectancy,
    profit_factor,
    review_verdict,
    runtime_allowed,
    execution_enabled
FROM runtime_review_package
ORDER BY id DESC
LIMIT 5;
"

echo TEST_RUNTIME_REVIEW_PACKAGE_V1_OK
