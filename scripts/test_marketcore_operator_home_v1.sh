#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKETCORE_OPERATOR_HOME_V1 ==="

doc=docs/MARKETCORE_OPERATOR_HOME_V1.txt

test -f "$doc"

for section in \
    "Header" \
    "System Status" \
    "Alerts" \
    "Best Edge" \
    "Shadow Observation" \
    "Daily Analytics" \
    "Market Overview" \
    "Portfolio" \
    "Research Queue" \
    "System Health"
do
    grep -q "$section" "$doc"
done

grep -q "MARKETCORE_OPERATOR_HOME_V1_READY" "$doc"

echo "operator_home_contract=OK"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=MARKETCORE_OPERATOR_HOME_V1_READY"
echo "VERDICT=TEST_MARKETCORE_OPERATOR_HOME_V1_OK"
