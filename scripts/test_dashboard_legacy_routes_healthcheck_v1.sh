#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_LEGACY_ROUTES_HEALTHCHECK_V1 ==="

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

out="$(mktemp)"

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_dashboard_legacy_routes_healthcheck_v1.py \
| tee "$out"

grep -q "TEST_DASHBOARD_LEGACY_ROUTES_HEALTHCHECK_V1_OK" "$out"

echo "VERDICT=DASHBOARD_LEGACY_ROUTES_HEALTHCHECK_TEST_OK"
echo "TEST_DASHBOARD_LEGACY_ROUTES_HEALTHCHECK_V1_OK"
