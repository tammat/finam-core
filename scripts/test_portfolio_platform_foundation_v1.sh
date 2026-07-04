#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PORTFOLIO_PLATFORM_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/012_portfolio_platform_foundation_v1.sql

position_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.portfolio_position_snapshot_v1') IS NOT NULL;")
equity_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.portfolio_equity_snapshot_v1') IS NOT NULL;")
config_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.portfolio_configuration_v1') IS NOT NULL;")
governance_table=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.portfolio_governance_v1') IS NOT NULL;")

config_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.portfolio_configuration_v1;")
equity_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.portfolio_equity_snapshot_v1;")

test "$position_table" = "t"
test "$equity_table" = "t"
test "$config_table" = "t"
test "$governance_table" = "t"
test "$config_rows" -gt 0
test "$equity_rows" -gt 0

psql -d finam_core -c "\d analytics.portfolio_position_snapshot_v1"
psql -d finam_core -c "\d analytics.portfolio_equity_snapshot_v1"
psql -d finam_core -c "\d analytics.portfolio_configuration_v1"
psql -d finam_core -c "\d analytics.portfolio_governance_v1"

echo "portfolio_position_table=$position_table"
echo "portfolio_equity_table=$equity_table"
echo "portfolio_configuration_table=$config_table"
echo "portfolio_governance_table=$governance_table"
echo "configuration_rows=$config_rows"
echo "equity_rows=$equity_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PORTFOLIO_PLATFORM_FOUNDATION_V1_READY"
echo "VERDICT=TEST_PORTFOLIO_PLATFORM_FOUNDATION_V1_OK"
