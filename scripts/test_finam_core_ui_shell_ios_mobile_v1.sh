#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_FINAM_CORE_UI_SHELL_IOS_MOBILE_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS \
  -H 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1' \
  "http://127.0.0.1:8088/" \
  > /tmp/finam_core_ios_mobile_v1.html

grep -q "Finam Core" /tmp/finam_core_ios_mobile_v1.html
grep -q "viewport" /tmp/finam_core_ios_mobile_v1.html
grep -q "🟢 ОК" /tmp/finam_core_ios_mobile_v1.html
grep -q "🟡 Набл." /tmp/finam_core_ios_mobile_v1.html
grep -q "🔴 Сделки отключены" /tmp/finam_core_ios_mobile_v1.html
grep -q "Кратко" /tmp/finam_core_ios_mobile_v1.html

curl -fsS "http://127.0.0.1:8088/" > /tmp/finam_core_desktop_v1.html
grep -q "Finam Core" /tmp/finam_core_desktop_v1.html
grep -q "Фьючерсы" /tmp/finam_core_desktop_v1.html

echo "VERDICT=FINAM_CORE_UI_SHELL_IOS_MOBILE_OK"
echo "TEST_FINAM_CORE_UI_SHELL_IOS_MOBILE_V1_OK"
