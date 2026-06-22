#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_CLEAN_SUBSET_DASHBOARD_ACCUMULATION_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/rs-bottom-clean)"

echo "$html" | grep -q "Накопление статистики"
echo "$html" | grep -q "Цель завершённых наблюдений"
echo "$html" | grep -q "Сейчас завершено"
echo "$html" | grep -q "Осталось до цели"
echo "$html" | grep -q "продолжать накопление статистики"
echo "$html" | grep -q "Реальная торговля"
echo "$html" | grep -q "запрещена"

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "DIRTY_OUTPUT_FOUND=1"
  exit 1
fi

echo "VERDICT=RS_BOTTOM_CLEAN_SUBSET_DASHBOARD_ACCUMULATION_OK"
echo "TEST_RS_BOTTOM_CLEAN_SUBSET_DASHBOARD_ACCUMULATION_V1_OK"
