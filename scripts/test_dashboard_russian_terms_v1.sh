#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DASHBOARD_RUSSIAN_TERMS_V1 ==="

pages=(
"/mobile"
"/edge"
"/rs-bottom-forward"
"/brent-rollover-edge"
)

for route in "${pages[@]}"; do

 html="$(curl -fsS "http://127.0.0.1:8088${route}")"

 echo "$html" | grep -q "Пробой\|Форвард\|Переносимость Brent\|Панель аналитики"

 if echo "$html" | grep -qi "Brent Rollover\|Breakout Readiness\|Finam Core Dashboard"; then
   echo "ENGLISH_TERM_FOUND route=${route}"
   exit 1
 fi

 echo "PAGE_OK route=${route}"

done

echo "VERDICT=DASHBOARD_RUSSIAN_TERMS_OK"
echo "TEST_DASHBOARD_RUSSIAN_TERMS_V1_OK"
