#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_FORWARD_LEADERBOARD_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/leaderboard)"

echo "$html" | grep -q "Лидеры исследований"
echo "$html" | grep -q "Выводы"
echo "$html" | grep -q "Главный вывод"
echo "$html" | grep -q "PF форвардной проверки"

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "DIRTY_OUTPUT_FOUND=1"
  exit 1
fi

if echo "$html" | grep -q "Нет данных форвардной проверки"; then
  echo "LEADERBOARD_DATA_STATUS=NO_FORWARD_DATA"
  exit 1
fi

echo "$html" | grep -q "BOTTOM"
echo "LEADERBOARD_DATA_STATUS=HAS_FORWARD_DATA"

echo "VERDICT=RS_BOTTOM_FORWARD_LEADERBOARD_OK"
echo "TEST_RS_BOTTOM_FORWARD_LEADERBOARD_V1_OK"
