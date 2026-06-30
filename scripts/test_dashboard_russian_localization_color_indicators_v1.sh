#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_DASHBOARD_RUSSIAN_LOCALIZATION_COLOR_INDICATORS_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 3

curl -fsS "http://127.0.0.1:8088/" \
  | tee /tmp/dashboard_russian_localization_color_indicators_v1.html >/dev/null

grep -q "RS Bottom: наблюдение без сделок V1" /tmp/dashboard_russian_localization_color_indicators_v1.html
grep -q "Состояние преимущества" /tmp/dashboard_russian_localization_color_indicators_v1.html
grep -q "ПОДТВЕРЖДЕНО" /tmp/dashboard_russian_localization_color_indicators_v1.html
grep -q "НАБЛЮДЕНИЕ" /tmp/dashboard_russian_localization_color_indicators_v1.html
grep -q "Макс. просадка" /tmp/dashboard_russian_localization_color_indicators_v1.html
grep -q "Средний результат" /tmp/dashboard_russian_localization_color_indicators_v1.html
grep -q "Доля успеха" /tmp/dashboard_russian_localization_color_indicators_v1.html
grep -q "background:#dcfce7" /tmp/dashboard_russian_localization_color_indicators_v1.html
grep -q "background:#fef3c7" /tmp/dashboard_russian_localization_color_indicators_v1.html
grep -q "background:#fee2e2" /tmp/dashboard_russian_localization_color_indicators_v1.html

if grep -Eq 'EDGE HEALTH|Runtime decision|Performance summary|Freshness|Collector|Max DD|Expectancy|Winrate' /tmp/dashboard_russian_localization_color_indicators_v1.html; then
  echo "VERDICT=DASHBOARD_RUSSIAN_LOCALIZATION_HAS_ENGLISH_LEFTOVERS"
  exit 1
fi

echo "VERDICT=DASHBOARD_RUSSIAN_LOCALIZATION_COLOR_INDICATORS_OK"
echo "TEST_DASHBOARD_RUSSIAN_LOCALIZATION_COLOR_INDICATORS_V1_OK"
