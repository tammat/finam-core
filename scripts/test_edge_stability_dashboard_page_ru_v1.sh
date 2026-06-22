#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_STABILITY_DASHBOARD_PAGE_RU_V1 ==="

html="$(curl -fsS http://127.0.0.1:8088/edge-stability)"

echo "$html" | grep -q "Устойчивость торгового преимущества"
echo "$html" | grep -q "Лучший результат исследования"
echo "$html" | grep -q "Реальный коэффициент прибыли"
echo "$html" | grep -q "Математическое ожидание"
echo "$html" | grep -q "Рейтинг кандидатов"
echo "$html" | grep -q "Доля успешных"
echo "$html" | grep -q "Выводы"

if echo "$html" | grep -qi "Traceback\|ModuleNotFoundError\|raw_json\|<pre>{"; then
  echo "DIRTY_OUTPUT_FOUND=1"
  exit 1
fi

if echo "$html" | grep -qi "Winrate\|Expectancy\|Real PF\|Verdict\|EDGE_STABLE_REAL_PF"; then
  echo "ENGLISH_OR_TECH_TERM_FOUND=1"
  exit 1
fi

echo "VERDICT=EDGE_STABILITY_DASHBOARD_PAGE_RU_OK"
echo "TEST_EDGE_STABILITY_DASHBOARD_PAGE_RU_V1_OK"
