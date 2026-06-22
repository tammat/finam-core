#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITY_STRATEGY_NAME_RESOLVER_PATCH_PLAN_V1 ==="

python3 -m py_compile \
src/scripts/runtime/build_equity_strategy_name_resolver_patch_plan_v1.py

python3 \
src/scripts/runtime/build_equity_strategy_name_resolver_patch_plan_v1.py \
| tee /tmp/equity_strategy_name_resolver_patch_plan_v1.log

grep -q \
"VERDICT=EQUITY_STRATEGY_NAME_RESOLVER_PATCH_PLAN_READY" \
/tmp/equity_strategy_name_resolver_patch_plan_v1.log

echo "TEST_EQUITY_STRATEGY_NAME_RESOLVER_PATCH_PLAN_V1_OK"
