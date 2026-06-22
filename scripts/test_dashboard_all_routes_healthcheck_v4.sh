#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_ALL_ROUTES_HEALTHCHECK_V4 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

routes=(
  "/mobile"
  "/summary"
  "/edge"
  "/rs-bottom-paper"
  "/rs-bottom-forward"
  "/rs-breakout-confirmation"
  "/compression-history"
  "/api/current"
)

failures=0

root_code="$(curl -sS -o /tmp/dashboard_root_body -w "%{http_code}" http://127.0.0.1:8088/ || true)"
root_location="$(curl -sSI http://127.0.0.1:8088/ | tr -d '\r' | awk -F': ' 'tolower($1)=="location"{print $2}' | tail -1)"

root_ok=0
if [ "$root_code" = "302" ] && [ "$root_location" = "/mobile" ]; then
  root_ok=1
else
  failures=$((failures + 1))
fi

echo "ROUTE_ROW route=/ http_status=${root_code} ok=${root_ok} location=${root_location}"

for route in "${routes[@]}"; do
  tmp="$(mktemp)"
  code="$(curl -sS -o "$tmp" -w "%{http_code}" "http://127.0.0.1:8088${route}" || true)"
  length="$(wc -c < "$tmp" | tr -d ' ')"

  ok=0
  if [ "$code" = "200" ] && [ "$length" -gt 20 ]; then
    ok=1
  else
    failures=$((failures + 1))
  fi

  echo "ROUTE_ROW route=${route} http_status=${code} ok=${ok} length=${length}"
  rm -f "$tmp"
done

echo "failures=${failures}"

if [ "$failures" -ne 0 ]; then
  echo "VERDICT=DASHBOARD_ALL_ROUTES_HEALTHCHECK_V4_FAILED"
  exit 1
fi

echo "VERDICT=DASHBOARD_ALL_ROUTES_HEALTHCHECK_V4_OK"
echo "TEST_DASHBOARD_ALL_ROUTES_HEALTHCHECK_V4_OK"
