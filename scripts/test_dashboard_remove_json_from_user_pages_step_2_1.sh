#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_REMOVE_JSON_FROM_USER_PAGES_STEP_2_1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

pages=(
  "/mobile"
  "/summary"
  "/edge"
  "/rs-bottom-paper"
  "/rs-bottom-forward"
  "/rs-breakout-confirmation"
  "/brent-rollover-edge"
  "/compression-history"
)

for route in "${pages[@]}"; do
  html="$(curl -fsS "http://127.0.0.1:8088${route}")"

  if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|Сырой вывод\|raw_json"; then
    echo "PAGE_FAILED route=${route}"
    exit 1
  fi

  if echo "$html" | grep -q "<pre>{"; then
    echo "PAYLOAD_FALLBACK_FOUND route=${route}"
    exit 1
  fi

  echo "PAGE_OK route=${route}"
done

echo "VERDICT=DASHBOARD_REMOVE_JSON_FROM_USER_PAGES_STEP_2_1_OK"
echo "TEST_DASHBOARD_REMOVE_JSON_FROM_USER_PAGES_STEP_2_1_OK"
