#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_DASHBOARD_MAIN_NAVIGATION_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

routes=(
  "/"
  "/rs-bottom-runtime-dry-run"
  "/active-futures-universe"
  "/equities"
  "/rs-bottom-forward"
  "/rs-bottom-clean"
  "/leaderboard"
  "/edge-stability"
)

for route in "${routes[@]}"; do
  out="/tmp/dashboard_nav_${route//\//_}.html"
  curl -fsS "http://127.0.0.1:8088${route}" > "$out"
  grep -q "Меню 8088" "$out"
  grep -q 'href="/"' "$out"
  grep -q 'href="/equities"' "$out"
  grep -q 'href="/rs-bottom-forward"' "$out"
  grep -q 'href="/active-futures-universe"' "$out"
  echo "PAGE_NAV_OK route=${route}"
done

echo "VERDICT=DASHBOARD_MAIN_NAVIGATION_OK"
echo "TEST_DASHBOARD_MAIN_NAVIGATION_V1_OK"
