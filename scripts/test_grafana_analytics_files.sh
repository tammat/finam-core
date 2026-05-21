#!/usr/bin/env bash
set -euo pipefail

test -f grafana/provisioning/datasources/postgres.yml
test -f grafana/provisioning/dashboards/dashboards.yml
test -f grafana/dashboards/finam_analytics.json

python -m json.tool grafana/dashboards/finam_analytics.json >/dev/null

grep -q "FinamCore PostgreSQL" grafana/provisioning/datasources/postgres.yml
grep -q "analytics_equity_curve" grafana/dashboards/finam_analytics.json
grep -q "analytics_drawdown_summary" grafana/dashboards/finam_analytics.json
grep -q "analytics_trade_statistics" grafana/dashboards/finam_analytics.json

echo "TEST_GRAFANA_ANALYTICS_FILES_OK"
