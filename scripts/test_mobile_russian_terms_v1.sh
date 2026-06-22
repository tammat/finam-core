#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MOBILE_RUSSIAN_TERMS_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/mobile)"

echo "$html" | grep -q "Монитор пробоя"
echo "$html" | grep -q "Исследование преимущества"
echo "$html" | grep -q "Состояние системы"
echo "$html" | grep -q "Форвардная проверка RS Bottom"
echo "$html" | grep -q "Переносимость Brent"
echo "$html" | grep -q "Панель аналитики"

if echo "$html" | grep -qi "Brent Rollover\|RS Bottom Forward\|RS Forward\|Breakout Confirmation\|NG Breakout\|BR Breakout\|Dashboard:\|Forward:"; then
  echo "MOBILE_ENGLISH_TERM_FOUND=1"
  exit 1
fi

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "MOBILE_DIRTY_TECH_OUTPUT_FOUND=1"
  exit 1
fi

echo "VERDICT=MOBILE_RUSSIAN_TERMS_OK"
echo "TEST_MOBILE_RUSSIAN_TERMS_V1_OK"
