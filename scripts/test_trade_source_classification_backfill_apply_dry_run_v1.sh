#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE SOURCE CLASSIFICATION BACKFILL APPLY DRY RUN V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/scripts/research/build_trade_source_classification_backfill_apply_dry_run_v1.py

PYTHONPATH=src python3 src/scripts/research/build_trade_source_classification_backfill_apply_dry_run_v1.py \
  | tee /tmp/trade_source_classification_backfill_apply_dry_run_v1.log

grep -q "TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_V1_OK" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log
grep -q "TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_SUMMARY" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log
grep -q "planned_updates=8323" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log
grep -q "already_classified=0" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log
grep -q "clean_runtime_or_paper_rows=688" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log
grep -q "historical_replay_rows=3752" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log
grep -q "legacy_ng_synthetic_backfill_rows=3326" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log
grep -q "apply_allowed=0" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log
grep -q "db_update=0" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log
grep -q "VERDICT=TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_READY" /tmp/trade_source_classification_backfill_apply_dry_run_v1.log

echo
echo "=== TRADE SOURCE CLASSIFICATION APPLY DRY RUN SUMMARY ==="
grep -E "TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_CLASS_ROW|rows_total=|planned_updates=|already_classified=|clean_runtime_or_paper_rows=|historical_replay_rows=|legacy_ng_synthetic_backfill_rows=|normalized_but_not_clean_edge_rows=|paper_fill_fallback_rows=|context_gap_review_rows=|no_payload_review_rows=|apply_allowed=|VERDICT=" \
  /tmp/trade_source_classification_backfill_apply_dry_run_v1.log

echo TEST_TRADE_SOURCE_CLASSIFICATION_BACKFILL_APPLY_DRY_RUN_V1_OK
