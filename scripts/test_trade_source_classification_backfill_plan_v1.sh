#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE SOURCE CLASSIFICATION BACKFILL PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_trade_source_classification_backfill_plan_v1.py

PYTHONPATH=src python3 src/scripts/research/build_trade_source_classification_backfill_plan_v1.py \
  | tee /tmp/trade_source_classification_backfill_plan_v1.log

grep -q "TRADE_SOURCE_CLASSIFICATION_BACKFILL_PLAN_V1_OK" /tmp/trade_source_classification_backfill_plan_v1.log
grep -q "TRADE_SOURCE_CLASSIFICATION_BACKFILL_PLAN_SUMMARY" /tmp/trade_source_classification_backfill_plan_v1.log
grep -q "planned_updates=" /tmp/trade_source_classification_backfill_plan_v1.log
grep -q "clean_runtime_or_paper_rows=" /tmp/trade_source_classification_backfill_plan_v1.log
grep -q "historical_replay_rows=" /tmp/trade_source_classification_backfill_plan_v1.log
grep -q "legacy_ng_synthetic_backfill_rows=" /tmp/trade_source_classification_backfill_plan_v1.log
grep -q "VERDICT=" /tmp/trade_source_classification_backfill_plan_v1.log
grep -q "db_update=0" /tmp/trade_source_classification_backfill_plan_v1.log

echo
echo "=== TRADE SOURCE CLASSIFICATION BACKFILL PLAN SUMMARY ==="
grep -E "TRADE_SOURCE_CLASSIFICATION_BACKFILL_CLASS_ROW|rows_total=|planned_updates=|already_classified=|clean_runtime_or_paper_rows=|historical_replay_rows=|legacy_ng_synthetic_backfill_rows=|paper_fill_fallback_rows=|context_gap_review_rows=|no_payload_review_rows=|VERDICT=" \
  /tmp/trade_source_classification_backfill_plan_v1.log

echo TEST_TRADE_SOURCE_CLASSIFICATION_BACKFILL_PLAN_V1_OK
