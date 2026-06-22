#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_NAVIGATION_AND_NUMBER_FORMAT_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/rs-bottom-clean)"

echo "$html" | grep -q "🏠 Главная"
echo "$html" | grep -q "Главная → RS Bottom очищенный"
echo "$html" | grep -q "Лидеры исследований"
echo "$html" | grep -q "Устойчивость преимущества"
echo "$html" | grep -q "RS Bottom очищенный"

if echo "$html" | grep -E "0\.[0-9]{10,}|[0-9]+\.[0-9]{10,}" >/dev/null; then
  echo "LONG_NUMBER_FOUND=1"
  exit 1
fi

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "DIRTY_OUTPUT_FOUND=1"
  exit 1
fi

echo "VERDICT=DASHBOARD_NAVIGATION_AND_NUMBER_FORMAT_OK"
echo "TEST_DASHBOARD_NAVIGATION_AND_NUMBER_FORMAT_V1_OK"
