#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST APPLY TRADE CONTEXT BACKFILL FROM PAYLOAD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile \
  src/scripts/research/apply_trade_context_backfill_from_payload_v1.py

PYTHONPATH=src python3 src/scripts/research/apply_trade_context_backfill_from_payload_v1.py \
  | tee /tmp/apply_trade_context_backfill_from_payload_v1_dry_run.log

grep -q "APPLY_TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_V1_OK" /tmp/apply_trade_context_backfill_from_payload_v1_dry_run.log
grep -q "VERDICT=TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_DRY_RUN_READY" /tmp/apply_trade_context_backfill_from_payload_v1_dry_run.log
grep -q "strategy_updates=127" /tmp/apply_trade_context_backfill_from_payload_v1_dry_run.log
grep -q "timeframe_updates=127" /tmp/apply_trade_context_backfill_from_payload_v1_dry_run.log
grep -q "continuous_symbol_updates=138" /tmp/apply_trade_context_backfill_from_payload_v1_dry_run.log

echo TEST_APPLY_TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_V1_OK
