#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL CLASS NORMALIZATION BACKFILL PLAN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_signal_class_normalization_backfill_plan_v1.py

PYTHONPATH=src python3 src/scripts/research/build_signal_class_normalization_backfill_plan_v1.py \
  | tee /tmp/signal_class_normalization_backfill_plan_v1.log

grep -q "SIGNAL_CLASS_NORMALIZATION_BACKFILL_PLAN_V1_OK" /tmp/signal_class_normalization_backfill_plan_v1.log
grep -q "SIGNAL_CLASS_NORMALIZATION_BACKFILL_PLAN_SUMMARY" /tmp/signal_class_normalization_backfill_plan_v1.log
grep -q "planned_updates=" /tmp/signal_class_normalization_backfill_plan_v1.log
grep -q "missing_signal_class=" /tmp/signal_class_normalization_backfill_plan_v1.log
grep -q "dynamic_reason_rows=" /tmp/signal_class_normalization_backfill_plan_v1.log
grep -q "db_update=0" /tmp/signal_class_normalization_backfill_plan_v1.log
grep -q "VERDICT=" /tmp/signal_class_normalization_backfill_plan_v1.log

echo
echo "=== SIGNAL CLASS NORMALIZATION BACKFILL PLAN SUMMARY ==="
grep -E "planned_updates=|missing_signal_class=|dynamic_reason_rows=|unknown_source_rows=|missing_strategy_rows=|missing_timeframe_rows=|normalized_classes=|VERDICT=" \
  /tmp/signal_class_normalization_backfill_plan_v1.log

echo TEST_SIGNAL_CLASS_NORMALIZATION_BACKFILL_PLAN_V1_OK
