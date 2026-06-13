#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_gold_runtime_review_gate_v1.py

python3 src/scripts/runtime/build_gold_runtime_review_gate_v1.py \
  | tee /tmp/gold_runtime_review_gate_v1.log

grep -q "GOLD RUNTIME REVIEW GATE V1" /tmp/gold_runtime_review_gate_v1.log
grep -q "REVIEW_GATE_ROW" /tmp/gold_runtime_review_gate_v1.log
grep -q "mandatory_filter_rule=up_impulse_sell_block" /tmp/gold_runtime_review_gate_v1.log
grep -q "runtime_allowed=0" /tmp/gold_runtime_review_gate_v1.log
grep -q "execution_enabled=0" /tmp/gold_runtime_review_gate_v1.log
grep -q "GOLD_RUNTIME_REVIEW_GATE_V1_OK" /tmp/gold_runtime_review_gate_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    registry_status,
    mandatory_filter_rule,
    stability_verdict,
    decision,
    runtime_allowed,
    execution_enabled
FROM gold_runtime_review_gate
ORDER BY id DESC
LIMIT 1;
" | tee /tmp/gold_runtime_review_gate_db_v1.log

grep -q "GDU6@RTSX" /tmp/gold_runtime_review_gate_db_v1.log
grep -q "up_impulse_sell_block" /tmp/gold_runtime_review_gate_db_v1.log
grep -q " f " /tmp/gold_runtime_review_gate_db_v1.log

echo TEST_GOLD_RUNTIME_REVIEW_GATE_V1_OK
