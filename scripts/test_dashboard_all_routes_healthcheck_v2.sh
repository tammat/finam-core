#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_ALL_ROUTES_HEALTHCHECK_V2 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

routes=(
  "/summary"
  "/edge"
  "/rs-bottom-paper"
  "/rs-bottom-forward"
  "/compression-history"
  "/api/current"
)

failures=0

for route in "${routes[@]}"; do
  body="$(mktemp)"
  code="$(curl -sS -o "$body" -w "%{http_code}" "http://127.0.0.1:8088${route}" || true)"
  length="$(wc -c < "$body" | tr -d ' ')"

  ok=0
  if [ "$code" = "200" ] && [ "$length" -gt 20 ]; then
    ok=1
  else
    failures=$((failures + 1))
  fi

  echo "ROUTE_ROW route=${route} http_status=${code} ok=${ok} length=${length}"

  rm -f "$body"
done

echo "failures=${failures}"

if [ "$failures" -ne 0 ]; then
  echo "VERDICT=DASHBOARD_ALL_ROUTES_HEALTHCHECK_V2_FAILED"
  exit 1
fi

echo "VERDICT=DASHBOARD_ALL_ROUTES_HEALTHCHECK_V2_OK"
echo "TEST_DASHBOARD_ALL_ROUTES_HEALTHCHECK_V2_OK"
