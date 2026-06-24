#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_DASHBOARD_MENU_RETURN_COMMISSION_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

home="/tmp/dashboard_menu_return_commission_v1_home.html"
archive="/tmp/dashboard_menu_return_commission_v1_archive.html"

curl -fsS "http://127.0.0.1:8088/" > "$home"
curl -fsS "http://127.0.0.1:8088/archive" > "$archive"

grep -q "Фьючерсы" "$home"
grep -q "Акции" "$home"
grep -q "История" "$home"
grep -q "Edge" "$home"
grep -q "Архив" "$home"

grep -q "Доход, %" "$home"
grep -q "Средний, %" "$home"
grep -q "Комиссия, %" "$home"
grep -q "Чистый доход, %" "$home"

grep -q "Архив 8088" "$archive"
grep -q "RS Bottom очищенный" "$archive"
grep -q "Сервисный API" "$archive"

# В главном меню не должно быть перегруза служебными страницами.
if grep -q 'RS Bottom paper</a>' "$home"; then
  echo "VERDICT=DASHBOARD_MENU_STILL_OVERLOADED"
  exit 1
fi

echo "VERDICT=DASHBOARD_MENU_RETURN_COMMISSION_OK"
echo "TEST_DASHBOARD_MENU_RETURN_COMMISSION_V1_OK"
