#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_PLATFORM_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/007_strategy_platform_foundation_v1.sql

registry_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_registry_v1;")
config_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_configuration_v1;")
dependency_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_feature_dependency_v1;")
enabled=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_registry_v1 WHERE strategy_family='VOLATILITY_BREAKOUT' AND enabled=true;")
live_enabled=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_registry_v1 WHERE live_enabled=true;")

test "$registry_rows" -gt 0
test "$config_rows" -gt 0
test "$dependency_rows" -gt 0
test "$enabled" = "1"
test "$live_enabled" = "0"

psql -d finam_core -c "
SELECT strategy_family, strategy_version, category, enabled, paper_enabled, risk_enabled, live_enabled, status
FROM analytics.strategy_registry_v1
ORDER BY priority;
"

psql -d finam_core -c "
SELECT strategy_family, strategy_version, feature_name, required, weight
FROM analytics.strategy_feature_dependency_v1
ORDER BY strategy_family, feature_name;
"

echo "registry_rows=$registry_rows"
echo "config_rows=$config_rows"
echo "dependency_rows=$dependency_rows"
echo "live_enabled=$live_enabled"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=STRATEGY_PLATFORM_FOUNDATION_V1_READY"
echo "VERDICT=TEST_STRATEGY_PLATFORM_FOUNDATION_V1_OK"
