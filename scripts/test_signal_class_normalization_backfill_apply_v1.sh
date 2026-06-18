#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL CLASS NORMALIZATION BACKFILL APPLY V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/apply_signal_class_normalization_backfill_v1.py

PYTHONPATH=src python3 src/scripts/research/apply_signal_class_normalization_backfill_v1.py \
  | tee /tmp/signal_class_normalization_backfill_apply_v1_dry_run.log

grep -q "SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_V1_OK" /tmp/signal_class_normalization_backfill_apply_v1_dry_run.log
grep -q "VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_DRY_RUN_READY" /tmp/signal_class_normalization_backfill_apply_v1_dry_run.log
grep -q "db_update=0" /tmp/signal_class_normalization_backfill_apply_v1_dry_run.log
grep -q "safe_updates=" /tmp/signal_class_normalization_backfill_apply_v1_dry_run.log
grep -q "review_only=" /tmp/signal_class_normalization_backfill_apply_v1_dry_run.log

APPLY=1 PYTHONPATH=src python3 src/scripts/research/apply_signal_class_normalization_backfill_v1.py \
  | tee /tmp/signal_class_normalization_backfill_apply_v1_apply.log

grep -q "SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_V1_OK" /tmp/signal_class_normalization_backfill_apply_v1_apply.log
grep -Eq "VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_OK|VERDICT=SIGNAL_CLASS_NORMALIZATION_BACKFILL_ALREADY_APPLIED" \
  /tmp/signal_class_normalization_backfill_apply_v1_apply.log
grep -q "db_update=1" /tmp/signal_class_normalization_backfill_apply_v1_apply.log

echo
echo "=== SIGNAL CLASS NORMALIZATION BACKFILL APPLY SUMMARY ==="
grep -E "rows_total=|safe_updates=|review_only=|unknown_reason_rows=|unknown_source_rows=|updated_rows=|VERDICT=" \
  /tmp/signal_class_normalization_backfill_apply_v1_apply.log

echo TEST_SIGNAL_CLASS_NORMALIZATION_BACKFILL_APPLY_V1_OK
