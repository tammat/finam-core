#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL CLASS NORMALIZATION BACKFILL APPLY DRY RUN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_signal_class_normalization_backfill_apply_dry_run_v1.py

PYTHONPATH=src python3 src/scripts/research/build_signal_class_normalization_backfill_apply_dry_run_v1.py \
  | tee /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log

grep -q "SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_DRY_RUN_V1_OK" /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log
grep -q "SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_DRY_RUN_SUMMARY" /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log
grep -q "safe_updates=" /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log
grep -q "review_only=" /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log
grep -q "unknown_reason_rows=" /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log
grep -q "db_update=0" /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log
grep -q "recommended_apply_requires_manual_confirmation=1" /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log
grep -q "VERDICT=" /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log

echo
echo "=== SIGNAL CLASS NORMALIZATION BACKFILL APPLY DRY RUN SUMMARY ==="
grep -E "rows_total=|safe_updates=|review_only=|unknown_reason_rows=|unknown_source_rows=|missing_strategy_rows=|missing_timeframe_rows=|existing_signal_class_rows=|VERDICT=" \
  /tmp/signal_class_normalization_backfill_apply_dry_run_v1.log

echo TEST_SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_DRY_RUN_V1_OK
