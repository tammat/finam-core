#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST LOW LEVEL ORDER CLIENT LAST LINE GUARD REVIEW V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/scripts/research/build_low_level_order_client_last_line_guard_review_v1.py \
  src/finam_core/risk/futures_real_block_guard_v1.py \
  src/finam_core/execution/finam_order_client_adapter.py \
  src/finam_core/execution/execution_dispatcher.py \
  src/finam_core/execution/oco_order_manager.py \
  src/scripts/run_synthetic_protective_real_sell_adapter.py

PYTHONPATH=src python3 src/scripts/research/build_low_level_order_client_last_line_guard_review_v1.py \
  | tee /tmp/low_level_order_client_last_line_guard_review_v1.log

grep -q "LOW_LEVEL_ORDER_CLIENT_LAST_LINE_GUARD_REVIEW_V1_OK" /tmp/low_level_order_client_last_line_guard_review_v1.log
grep -q "VERDICT=LOW_LEVEL_ORDER_CLIENT_LAST_LINE_GUARD_REVIEW_COMPLETE" /tmp/low_level_order_client_last_line_guard_review_v1.log
grep -q "primary_guard_complete=1" /tmp/low_level_order_client_last_line_guard_review_v1.log
grep -q "PRIMARY_GUARD_MISSING=none" /tmp/low_level_order_client_last_line_guard_review_v1.log
grep -q "LOW_LEVEL_GRPC_LAST_LINE_GUARD_CANDIDATE" /tmp/low_level_order_client_last_line_guard_review_v1.log
grep -q "LEGACY_REAL_EXECUTION_DEPRECATE_OR_GUARD" /tmp/low_level_order_client_last_line_guard_review_v1.log
grep -q "LEGACY_INFRA_USAGE_REVIEW" /tmp/low_level_order_client_last_line_guard_review_v1.log
grep -q "LOW_LEVEL_GUARD_CANDIDATES=src/finam_core/adapters/grpc/orders_client.py" /tmp/low_level_order_client_last_line_guard_review_v1.log
grep -q "MISSING_FILES=none" /tmp/low_level_order_client_last_line_guard_review_v1.log

echo
echo "=== LOW LEVEL REVIEW SUMMARY ==="
grep -E "PRIMARY_GUARD_STATUS|primary_guard_complete|LOW_LEVEL_REVIEW_SUMMARY|LOW_LEVEL_GUARD_CANDIDATES|LEGACY_REVIEW|VERDICT" \
  /tmp/low_level_order_client_last_line_guard_review_v1.log

echo TEST_LOW_LEVEL_ORDER_CLIENT_LAST_LINE_GUARD_REVIEW_V1_OK
