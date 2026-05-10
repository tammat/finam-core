#!/usr/bin/env bash
set -euo pipefail

test -f ops/grafana/docker-compose.yml
test -f ops/grafana/provisioning/datasources/postgres.yml
test -f ops/grafana/provisioning/dashboards/dashboards.yml
test -f ops/grafana/dashboards/finam-production.json
test -x scripts/install_grafana.sh

grep -q "FinamPostgres" ops/grafana/provisioning/datasources/postgres.yml
grep -q "v_production_health" ops/grafana/dashboards/finam-production.json
grep -q "Задержка projections" ops/grafana/dashboards/finam-production.json
grep -q "DLQ нерешённые" ops/grafana/dashboards/finam-production.json

echo "GRAFANA_PROVISIONING_OK"
