#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST FUTURES REAL BLOCK GUARD FINAL HEALTHCHECK V1 ==="

export RUNTIME_ALLOW=0
export EXECUTION_ENABLED=0
export REAL_TRADING_ENABLED=0

echo "runtime_allow=${RUNTIME_ALLOW}"
echo "execution_enabled=${EXECUTION_ENABLED}"
echo "real_trading_enabled=${REAL_TRADING_ENABLED}"

python3 -m py_compile \
  src/finam_core/risk/futures_real_block_guard_v1.py \
  src/finam_core/execution/finam_order_client_adapter.py \
  src/finam_core/execution/execution_dispatcher.py \
  src/finam_core/execution/oco_order_manager.py \
  src/scripts/run_synthetic_protective_real_sell_adapter.py \
  src/scripts/research/build_futures_real_block_guard_protective_wiring_audit_v2.py \
  src/scripts/research/build_futures_real_block_guard_final_healthcheck_v1.py

PYTHONPATH=src python3 src/scripts/research/build_futures_real_block_guard_final_healthcheck_v1.py \
  | tee /tmp/futures_real_block_guard_final_healthcheck_v1.log

grep -q "FUTURES_REAL_BLOCK_GUARD_FINAL_HEALTHCHECK_V1_OK" /tmp/futures_real_block_guard_final_healthcheck_v1.log
grep -q "VERDICT=FUTURES_REAL_BLOCK_GUARD_FINAL_HEALTHCHECK_OK" /tmp/futures_real_block_guard_final_healthcheck_v1.log
grep -q "marker_missing=0" /tmp/futures_real_block_guard_final_healthcheck_v1.log
grep -q "guard_failures=0" /tmp/futures_real_block_guard_final_healthcheck_v1.log
grep -q "safety_failures=0" /tmp/futures_real_block_guard_final_healthcheck_v1.log
grep -q "SAFETY_FAILURES=none" /tmp/futures_real_block_guard_final_healthcheck_v1.log
grep -q "GUARD_FAILURES=none" /tmp/futures_real_block_guard_final_healthcheck_v1.log
grep -q "MARKER_MISSING=none" /tmp/futures_real_block_guard_final_healthcheck_v1.log

echo
echo "=== RE-RUN CORE GUARD TESTS ==="

bash scripts/test_futures_real_block_guard_broker_wiring_v1.sh
bash scripts/test_futures_real_block_guard_dispatcher_wiring_v1.sh
bash scripts/test_futures_real_block_guard_synthetic_protective_wiring_v1.sh
bash scripts/test_futures_real_block_guard_oco_wiring_v1.sh
bash scripts/test_futures_real_block_guard_protective_wiring_audit_v2.sh

echo TEST_FUTURES_REAL_BLOCK_GUARD_FINAL_HEALTHCHECK_V1_OK
