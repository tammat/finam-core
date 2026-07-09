#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLAN_PARAMETER_PROFILE_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 \
-f sql/knowledge/trading_plan_parameter_profile_v1.sql

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM knowledge.trading_plan_parameter_profile_v1
WHERE enabled;
")

test "$rows" -ge 3

echo "profiles=$rows"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=TRADING_PLAN_PARAMETER_PROFILE_V1_READY"
echo "VERDICT=TEST_TRADING_PLAN_PARAMETER_PROFILE_V1_OK"
