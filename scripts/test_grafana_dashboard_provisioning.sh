#!/usr/bin/env bash
set -euo pipefail

test -f infra/grafana/provisioning/dashboards/finam_core_dashboards.yml
grep -q "Finam Core Dashboards" infra/grafana/provisioning/dashboards/finam_core_dashboards.yml
grep -q "/var/lib/grafana/dashboards" infra/grafana/provisioning/dashboards/finam_core_dashboards.yml

echo "TEST_GRAFANA_DASHBOARD_PROVISIONING_OK"
