#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST DIRTY TRADE ORIGIN PATCH PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_dirty_trade_origin_patch_plan_v1.py

PYTHONPATH=src python3 src/scripts/research/build_dirty_trade_origin_patch_plan_v1.py \
  | tee /tmp/dirty_trade_origin_patch_plan_v1.log

grep -q "DIRTY_TRADE_ORIGIN_PATCH_PLAN_V1_OK" /tmp/dirty_trade_origin_patch_plan_v1.log
grep -q "DIRTY_TRADE_ORIGIN_PATCH_PLAN_SUMMARY" /tmp/dirty_trade_origin_patch_plan_v1.log
grep -q "legacy_ng_synthetic_backfill_rows=" /tmp/dirty_trade_origin_patch_plan_v1.log
grep -q "historical_replay_rows=" /tmp/dirty_trade_origin_patch_plan_v1.log
grep -q "clean_runtime_or_paper_rows=" /tmp/dirty_trade_origin_patch_plan_v1.log
grep -q "VERDICT=" /tmp/dirty_trade_origin_patch_plan_v1.log
grep -q "db_update=0" /tmp/dirty_trade_origin_patch_plan_v1.log

echo
echo "=== DIRTY TRADE ORIGIN PATCH PLAN SUMMARY ==="
grep -E "DIRTY_TRADE_ORIGIN_PATCH_CLASS_ROW|rows_total=|clean_runtime_or_paper_rows=|historical_replay_rows=|legacy_ng_synthetic_backfill_rows=|context_gap_review_rows=|no_payload_review_rows=|VERDICT=" \
  /tmp/dirty_trade_origin_patch_plan_v1.log | head -120

echo TEST_DIRTY_TRADE_ORIGIN_PATCH_PLAN_V1_OK
