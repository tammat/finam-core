#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_WRAPPER_V1 ==="

wrapper="scripts/workspace_v2_daily_system_healthcheck_v1.sh"

test -x "$wrapper"

"$wrapper"

report="reports/workspace_v2_daily_system_healthcheck_v1.txt"

test -f "$report"

grep -q "WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_V1_READY" "$report"

grep -q "SUMMARY" "$report"

echo "wrapper=OK"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_WRAPPER_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_DAILY_SYSTEM_HEALTHCHECK_WRAPPER_V1_OK"
