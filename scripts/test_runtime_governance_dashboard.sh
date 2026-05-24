#!/usr/bin/env bash
set -euo pipefail

python3 -m json.tool \
  infra/grafana/dashboards/runtime_governance_dashboard.json \
  >/dev/null

grep -q "governance_decision" \
  infra/grafana/sql/runtime_governance_dashboard.sql

grep -q "BLOCKED_EVENT" \
  infra/grafana/sql/runtime_governance_dashboard.sql

grep -q "BLOCKED_SESSION" \
  infra/grafana/sql/runtime_governance_dashboard.sql

echo "TEST_RUNTIME_GOVERNANCE_DASHBOARD_OK"
