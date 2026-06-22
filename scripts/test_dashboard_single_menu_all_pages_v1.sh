#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_SINGLE_MENU_ALL_PAGES_V1 ==="

routes=(
  /mobile
  /leaderboard
  /edge-stability
  /rs-bottom-clean
)

markers=(
  "Главная"
  "Лидеры исследований"
  "Устойчивость преимущества"
  "RS Bottom очищенный"
  "Форвардная проверка RS Bottom"
)

for route in "${routes[@]}"; do
  html="$(curl -fsS "http://127.0.0.1:8088${route}")"

  for marker in "${markers[@]}"; do
    echo "$html" | grep -q "$marker" || {
      echo "MENU_MARKER_MISSING route=${route} marker=${marker}"
      exit 1
    }
  done

  if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
    echo "DIRTY_OUTPUT_FOUND route=${route}"
    exit 1
  fi

  echo "PAGE_OK route=${route}"
done

echo "VERDICT=DASHBOARD_SINGLE_MENU_ALL_PAGES_OK"
echo "TEST_DASHBOARD_SINGLE_MENU_ALL_PAGES_V1_OK"
