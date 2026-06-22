#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EQUITIES_DASHBOARD_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/equities)"

echo "$html" | grep -q "Акции"
echo "$html" | grep -q "Статус направления"
echo "$html" | grep -q "Активная вселенная акций"
echo "$html" | grep -q "Реальная торговля"
echo "$html" | grep -q "запрещена"
echo "$html" | grep -q "Инструмент"
echo "$html" | grep -q "Баров M1"
echo "$html" | grep -q "Баров M5"

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "DIRTY_OUTPUT_FOUND=1"
  exit 1
fi

echo "VERDICT=EQUITIES_DASHBOARD_OK"
echo "TEST_EQUITIES_DASHBOARD_V1_OK"
