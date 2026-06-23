#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_STABILITY_DASHBOARD_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/edge-stability)"

echo "$html" | grep -q "Лидер исследования"
echo "$html" | grep -q "Real PF"
echo "$html" | grep -q "Expectancy"
echo "$html" | grep -q "EDGE_STABLE_REAL_PF"

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError"; then
  echo "DIRTY_OUTPUT_FOUND=1"
  exit 1
fi

echo "VERDICT=EDGE_STABILITY_DASHBOARD_OK"
echo "TEST_EDGE_STABILITY_DASHBOARD_V1_OK"
