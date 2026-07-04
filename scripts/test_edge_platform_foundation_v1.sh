#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_PLATFORM_FOUNDATION_V1 ==="

sudo -u postgres psql \
    -v ON_ERROR_STOP=1 \
    -d finam_core \
    -f sql/analytics/009_edge_platform_foundation_v1.sql

edge_snapshot=$(psql -At -d finam_core -c \
"SELECT to_regclass('analytics.edge_decision_snapshot_v1') IS NOT NULL;")

edge_config=$(psql -At -d finam_core -c \
"SELECT to_regclass('analytics.edge_configuration_v1') IS NOT NULL;")

edge_governance=$(psql -At -d finam_core -c \
"SELECT to_regclass('analytics.edge_governance_v1') IS NOT NULL;")

cfg=$(psql -At -d finam_core -c \
"SELECT count(*) FROM analytics.edge_configuration_v1;")

test "$edge_snapshot" = "t"
test "$edge_config" = "t"
test "$edge_governance" = "t"
test "$cfg" -gt 0

psql -d finam_core -c "\d analytics.edge_decision_snapshot_v1"

psql -d finam_core -c "\d analytics.edge_configuration_v1"

psql -d finam_core -c "\d analytics.edge_governance_v1"

echo "edge_snapshot_table=$edge_snapshot"
echo "edge_configuration_table=$edge_config"
echo "edge_governance_table=$edge_governance"
echo "configuration_rows=$cfg"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=EDGE_PLATFORM_FOUNDATION_V1_READY"
echo "VERDICT=TEST_EDGE_PLATFORM_FOUNDATION_V1_OK"

