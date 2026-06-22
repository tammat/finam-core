#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_CLEAN_SUBSET_DASHBOARD_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/rs-bottom-clean)"

echo "$html" | grep -q "RS Bottom — очищенная версия"
echo "$html" | grep -q "Полная версия"
echo "$html" | grep -q "отклонена"
echo "$html" | grep -q "исследовательский кандидат"
echo "$html" | grep -q "Реальная торговля"
echo "$html" | grep -q "запрещена"
echo "$html" | grep -q "Очищенная выборка"
echo "$html" | grep -q "Реальный коэффициент прибыли"
echo "$html" | grep -q "Математическое ожидание"
echo "$html" | grep -q "BRN6@RTSX"

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "DIRTY_OUTPUT_FOUND=1"
  exit 1
fi

echo "VERDICT=RS_BOTTOM_CLEAN_SUBSET_DASHBOARD_OK"
echo "TEST_RS_BOTTOM_CLEAN_SUBSET_DASHBOARD_V1_OK"
