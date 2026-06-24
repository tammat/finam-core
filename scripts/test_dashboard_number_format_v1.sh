#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_DASHBOARD_NUMBER_FORMAT_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/" \
  | tee /tmp/dashboard_number_format_v1.html >/dev/null

grep -q "RS Bottom Runtime Dry Run V1" /tmp/dashboard_number_format_v1.html
grep -q "EDGE HEALTH" /tmp/dashboard_number_format_v1.html
grep -q "GDU6@RTSX" /tmp/dashboard_number_format_v1.html
grep -q "GLU6@RTSX" /tmp/dashboard_number_format_v1.html
grep -q "NGM6@RTSX" /tmp/dashboard_number_format_v1.html

# Не должно быть длинных хвостов PostgreSQL numeric на главной странице.
if grep -Eq '[0-9]+\.[0-9]{8,}' /tmp/dashboard_number_format_v1.html; then
  echo "VERDICT=DASHBOARD_NUMBER_FORMAT_HAS_LONG_DECIMALS"
  exit 1
fi

grep -q "%" /tmp/dashboard_number_format_v1.html

echo "VERDICT=DASHBOARD_NUMBER_FORMAT_OK"
echo "TEST_DASHBOARD_NUMBER_FORMAT_V1_OK"
