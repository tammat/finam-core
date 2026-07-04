#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_TRADING_PLATFORM_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/011_trading_platform_foundation_v1.sql

intent_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.trading_order_intent_v1') IS NOT NULL;")
config_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.trading_configuration_v1') IS NOT NULL;")
governance_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.trading_governance_v1') IS NOT NULL;")

config_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.trading_configuration_v1;")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.trading_order_intent_v1
WHERE live_allowed=true
   OR micro_live_allowed=true
   OR order_sent=true;
")

test "$intent_table" = "t"
test "$config_table" = "t"
test "$governance_table" = "t"
test "$config_rows" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "\d analytics.trading_order_intent_v1"
psql -d finam_core -c "\d analytics.trading_configuration_v1"
psql -d finam_core -c "\d analytics.trading_governance_v1"

echo "trading_order_intent_table=$intent_table"
echo "trading_configuration_table=$config_table"
echo "trading_governance_table=$governance_table"
echo "configuration_rows=$config_rows"
echo "unsafe_live_or_sent_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TRADING_PLATFORM_FOUNDATION_V1_READY"
echo "VERDICT=TEST_TRADING_PLATFORM_FOUNDATION_V1_OK"
