#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RS_BOTTOM_FORWARD_SCORECARD_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_rs_bottom_forward_scorecard_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_rs_bottom_forward_scorecard_v1.py | tee "$out"

grep -q "TEST_RS_BOTTOM_FORWARD_SCORECARD_V1_OK" "$out"
grep -q "VERDICT=RS_BOTTOM_FORWARD_SCORECARD_READY" "$out"
grep -q "db_update=1" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "СБОР_СТАТИСТИКИ" "$out"

psql "$DATABASE_URL" -c "
select
  selection as \"Селекция\",
  filter_name as \"Фильтр\",
  signals_total as \"Всего\",
  waiting as \"Ожидают\",
  success as \"Успешно\",
  failure as \"Неуспешно\",
  round(profit_factor_forward, 4) as \"PF forward\",
  round(profit_factor_historical, 4) as \"PF исторический\",
  verdict as \"Вердикт\"
from analytics_futures_rs_bottom_forward_scorecard_v1
order by profit_factor_historical desc;
"

echo "VERDICT=RS_BOTTOM_FORWARD_SCORECARD_TEST_OK"
echo "TEST_RS_BOTTOM_FORWARD_SCORECARD_V1_OK"
