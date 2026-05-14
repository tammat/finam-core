#!/usr/bin/env bash
set -euo pipefail

grep -q "Trailing Stop Movement" \
  ops/grafana/dashboards/finam-mobile.json

grep -q "trailing_order_events" \
  ops/grafana/dashboards/finam-mobile.json

python -m json.tool \
  ops/grafana/dashboards/finam-mobile.json >/dev/null

echo "OK: grafana trailing panel configured"
