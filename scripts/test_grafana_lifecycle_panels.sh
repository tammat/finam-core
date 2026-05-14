#!/usr/bin/env bash
set -euo pipefail

python -m json.tool ops/grafana/dashboards/finam-mobile.json >/dev/null

grep -q "Position Lifecycle State" ops/grafana/dashboards/finam-mobile.json
grep -q "Partial Close Status" ops/grafana/dashboards/finam-mobile.json
grep -q "Active Trailing Stops" ops/grafana/dashboards/finam-mobile.json
grep -q "Exit Lifecycle Audit" ops/grafana/dashboards/finam-mobile.json
grep -q "position_lifecycle_state" ops/grafana/dashboards/finam-mobile.json

echo "OK: lifecycle grafana panels configured"
