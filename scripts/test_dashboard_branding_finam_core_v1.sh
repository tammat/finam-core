#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_DASHBOARD_BRANDING_FINAM_CORE_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

home="/tmp/dashboard_branding_finam_core_v1_home.html"
archive="/tmp/dashboard_branding_finam_core_v1_archive.html"

curl -fsS "http://127.0.0.1:8088/" > "$home"
curl -fsS "http://127.0.0.1:8088/archive" > "$archive"

grep -q "Finam Core" "$home"
grep -q "Finam Core: наблюдение за edge" "$home"
grep -q "Архив Finam Core" "$archive"

if grep -q "Меню 8088\|Архив 8088" "$home" "$archive"; then
  echo "VERDICT=DASHBOARD_BRANDING_HAS_OLD_8088_LABELS"
  exit 1
fi

echo "VERDICT=DASHBOARD_BRANDING_FINAM_CORE_OK"
echo "TEST_DASHBOARD_BRANDING_FINAM_CORE_V1_OK"
