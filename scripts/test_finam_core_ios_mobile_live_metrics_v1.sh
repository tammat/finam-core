#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_FINAM_CORE_IOS_MOBILE_LIVE_METRICS_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

out="/tmp/finam_core_ios_mobile_live_metrics_v1.html"

curl -fsS \
  -H 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1' \
  "http://127.0.0.1:8088/" \
  > "$out"

grep -q "Finam Core" "$out"
grep -q "🟢 ОК" "$out"
grep -q "🟡 Набл." "$out"
grep -q "🔴 Сделки отключены" "$out"
grep -q "Доход:" "$out"
grep -q "Комиссия:" "$out"
grep -q "Чистый доход:" "$out"
grep -q "PF:" "$out"
grep -q "Просадка:" "$out"
grep -q "Обновлено:" "$out"
grep -q "GDU6@RTSX" "$out"
grep -q "GLU6@RTSX" "$out"
grep -q "NGM6@RTSX" "$out"

if grep -Eq '20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?\+00:00' "$out"; then
  echo "VERDICT=FINAM_CORE_IOS_MOBILE_HAS_RAW_UTC_TIMESTAMP"
  exit 1
fi

echo "VERDICT=FINAM_CORE_IOS_MOBILE_LIVE_METRICS_OK"
echo "TEST_FINAM_CORE_IOS_MOBILE_LIVE_METRICS_V1_OK"
