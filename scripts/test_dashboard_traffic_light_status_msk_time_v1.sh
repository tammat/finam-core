#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_DASHBOARD_TRAFFIC_LIGHT_STATUS_MSK_TIME_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

routes=(
  "/"
  "/active-futures-universe"
  "/equities"
  "/rs-bottom-forward"
  "/edge-stability"
  "/archive"
  "/rs-bottom-runtime-dry-run"
  "/leaderboard"
  "/rs-bottom-clean"
  "/rs-bottom-paper"
)

for route in "${routes[@]}"; do
  out="/tmp/dashboard_traffic_msk_${route//\//_}.html"
  curl -fsS "http://127.0.0.1:8088${route}" > "$out"

  grep -q "Finam Core" "$out"
  grep -q 'href="/"' "$out"

  if grep -Eq '20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?\+00:00' "$out"; then
    echo "RAW_UTC_TIMESTAMP_FOUND route=${route}"
    exit 1
  fi

  echo "PAGE_MSK_TIME_OK route=${route}"
done

home="/tmp/dashboard_traffic_msk__.html"

grep -Eq "🟢|🟡|🔴" "$home"
grep -q "🟢 ОК" "$home"
grep -q "🟡 Набл." "$home"
grep -q "🔴 РИСК" "$home"

grep -Eq '[0-9]{2}\.[а-я]{3}\.[0-9]{4} [0-9]{2}:[0-9]{2} МСК' "$home"

echo "VERDICT=DASHBOARD_TRAFFIC_LIGHT_STATUS_MSK_TIME_OK"
echo "TEST_DASHBOARD_TRAFFIC_LIGHT_STATUS_MSK_TIME_V1_OK"
