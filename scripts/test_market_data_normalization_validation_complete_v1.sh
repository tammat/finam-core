#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_NORMALIZATION_VALIDATION_COMPLETE_V1 ==="

scripts/test_market_data_normalization_validation_v1.sh >/tmp/v1.out
scripts/test_market_data_normalization_dry_run_v1.sh >/tmp/v2.out
scripts/test_market_data_normalization_reject_v1.sh >/tmp/v3.out
scripts/test_market_data_normalization_idempotency_v1.sh >/tmp/v4.out

grep -q TEST_MARKET_DATA_NORMALIZATION_VALIDATION_V1_OK /tmp/v1.out
grep -q TEST_MARKET_DATA_NORMALIZATION_DRY_RUN_V1_OK /tmp/v2.out
grep -q TEST_MARKET_DATA_NORMALIZATION_REJECT_V1_OK /tmp/v3.out
grep -q TEST_MARKET_DATA_NORMALIZATION_IDEMPOTENCY_V1_OK /tmp/v4.out

echo "validation=READY"
echo "dry_run=READY"
echo "reject=READY"
echo "idempotency=READY"

echo "validation_complete=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKET_DATA_NORMALIZATION_VALIDATION_COMPLETE_V1_READY"
echo "TEST_MARKET_DATA_NORMALIZATION_VALIDATION_COMPLETE_V1_OK"
