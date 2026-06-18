#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT BACKFILL FROM PAYLOAD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_trade_context_backfill_from_payload_v1.py

PYTHONPATH=src python3 src/scripts/research/build_trade_context_backfill_from_payload_v1.py \
  | tee /tmp/trade_context_backfill_from_payload_v1.log

grep -q "TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_V1_OK" /tmp/trade_context_backfill_from_payload_v1.log
grep -q "TRADE_CONTEXT_BACKFILL_PREVIEW_SUMMARY" /tmp/trade_context_backfill_from_payload_v1.log
grep -q "VERDICT=" /tmp/trade_context_backfill_from_payload_v1.log

echo TEST_TRADE_CONTEXT_BACKFILL_FROM_PAYLOAD_V1_OK
