#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MOBILE_RESEARCH_SUMMARY_RU_INDICATORS_V1 ==="

python3 -m py_compile src/scripts/research/serve_multi_asset_breakout_dashboard_v1.py

sudo systemctl restart finam-multi-asset-breakout-dashboard.service
sleep 5

html="$(curl -fsS http://127.0.0.1:8088/mobile)"

echo "$html" | grep -q "мобильная сводка"
echo "$html" | grep -q "Фьючерсы"
echo "$html" | grep -q "Акции"
echo "$html" | grep -q "Индикаторы"
echo "$html" | grep -q "Реальная торговля"
echo "$html" | grep -q "ГЛАВНЫЙ КАНДИДАТ"
echo "$html" | grep -q "ОТРИЦАТЕЛЬНО"

echo "VERDICT=MOBILE_RESEARCH_SUMMARY_RU_INDICATORS_OK"
echo "TEST_MOBILE_RESEARCH_SUMMARY_RU_INDICATORS_V1_OK"
