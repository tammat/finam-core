#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TRADE CONTEXT SNAPSHOT COMPLETENESS V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_trade_context_snapshot_completeness_v1.py

PYTHONPATH=src python3 src/scripts/research/build_trade_context_snapshot_completeness_v1.py \
  | tee /tmp/trade_context_snapshot_completeness_v1.log

grep -q "TRADE_CONTEXT_SNAPSHOT_COMPLETENESS_V1_OK" /tmp/trade_context_snapshot_completeness_v1.log
grep -q "VERDICT=TRADE_CONTEXT_SNAPSHOT_COMPLETENESS_REVIEW_READY" /tmp/trade_context_snapshot_completeness_v1.log
grep -q "TRADE_CONTEXT_COMPLETENESS_SUMMARY" /tmp/trade_context_snapshot_completeness_v1.log
grep -q "TRADE_CONTEXT_ROW" /tmp/trade_context_snapshot_completeness_v1.log

echo TEST_TRADE_CONTEXT_SNAPSHOT_COMPLETENESS_V1_OK
