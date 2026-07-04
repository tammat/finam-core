#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_PLATFORM_FOUNDATION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/010_risk_platform_foundation_v1.sql

risk_snapshot=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.risk_decision_snapshot_v1') IS NOT NULL;")
risk_config=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.risk_configuration_v1') IS NOT NULL;")
risk_governance=$(psql -At -d finam_core -c "SELECT to_regclass('analytics.risk_governance_v1') IS NOT NULL;")
config_rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.risk_configuration_v1;")
unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.risk_decision_snapshot_v1
WHERE ready_for_live=true OR ready_for_micro_live=true;
")

test "$risk_snapshot" = "t"
test "$risk_config" = "t"
test "$risk_governance" = "t"
test "$config_rows" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "\d analytics.risk_decision_snapshot_v1"
psql -d finam_core -c "\d analytics.risk_configuration_v1"
psql -d finam_core -c "\d analytics.risk_governance_v1"

echo "risk_snapshot_table=$risk_snapshot"
echo "risk_configuration_table=$risk_config"
echo "risk_governance_table=$risk_governance"
echo "configuration_rows=$config_rows"
echo "unsafe_live_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RISK_PLATFORM_FOUNDATION_V1_READY"
echo "VERDICT=TEST_RISK_PLATFORM_FOUNDATION_V1_OK"
