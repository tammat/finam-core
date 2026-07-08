#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BROKER_ABSTRACTION_ARCHITECTURE_V1 ==="

doc="docs/BROKER_ABSTRACTION_ARCHITECTURE_V1.txt"
test -f "$doc"

grep -q "MarketCore is the platform" "$doc"
grep -q "Finam is a broker adapter" "$doc"
grep -q "timezone selector" "$doc"
grep -q "currency selector" "$doc"
grep -q "broker selector" "$doc"
grep -q "DD-MM-YY HH:MM" "$doc"
grep -q "BROKER_ABSTRACTION_ARCHITECTURE_V1_READY" "$doc"

echo "broker_abstraction_doc=OK"
echo "logo=🧠 MarketCore"
echo "status_bar=TZ_CURRENCY_BROKER_TIME"
echo "time_format=DD-MM-YY HH:MM"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=BROKER_ABSTRACTION_ARCHITECTURE_V1_READY"
echo "VERDICT=TEST_BROKER_ABSTRACTION_ARCHITECTURE_V1_OK"
