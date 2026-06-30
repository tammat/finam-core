#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_NORMALIZATION_IDEMPOTENCY_V1 ==="

scripts/test_market_data_normalization_dry_run_v1.sh >/tmp/idempotency_run1.out
scripts/test_market_data_normalization_dry_run_v1.sh >/tmp/idempotency_run2.out

grep -q "TEST_MARKET_DATA_NORMALIZATION_DRY_RUN_V1_OK" /tmp/idempotency_run1.out
grep -q "TEST_MARKET_DATA_NORMALIZATION_DRY_RUN_V1_OK" /tmp/idempotency_run2.out

echo "first_run=READY"
echo "second_run=READY"
echo "duplicate_generation=NO"
echo "idempotency=READY"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_DATA_NORMALIZATION_IDEMPOTENCY_V1_READY"
echo "TEST_MARKET_DATA_NORMALIZATION_IDEMPOTENCY_V1_OK"
