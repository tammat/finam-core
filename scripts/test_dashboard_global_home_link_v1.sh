#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_DASHBOARD_GLOBAL_HOME_LINK_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

routes=(
  "/"
  "/rs-bottom-runtime-dry-run"
  "/active-futures-universe"
  "/rs-bottom-forward"
  "/rs-bottom-clean"
  "/leaderboard"
  "/edge-stability"
)

for route in "${routes[@]}"; do
  out="/tmp/dashboard_home_link_${route//\//_}.html"
  curl -fsS "http://127.0.0.1:8088${route}" > "$out"
  grep -q 'href="/"' "$out"
  grep -q 'Главная' "$out"
  echo "PAGE_HOME_LINK_OK route=${route}"
done

echo "TEST_DASHBOARD_GLOBAL_HOME_LINK_V1_OK"
