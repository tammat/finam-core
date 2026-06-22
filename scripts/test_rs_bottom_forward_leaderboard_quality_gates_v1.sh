#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_FORWARD_LEADERBOARD_QUALITY_GATES_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/leaderboard)"

echo "$html" | grep -q "Quality score"
echo "$html" | grep -q "Подтверждённый кандидат"
echo "$html" | grep -q "Статистическая аномалия"
echo "$html" | grep -q "BOTTOM3"

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "DIRTY_OUTPUT_FOUND=1"
  exit 1
fi

echo "VERDICT=RS_BOTTOM_FORWARD_LEADERBOARD_QUALITY_GATES_OK"
echo "TEST_RS_BOTTOM_FORWARD_LEADERBOARD_QUALITY_GATES_V1_OK"
