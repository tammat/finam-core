#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FUTURES_RS_BOTTOM_PAPER_OBSERVATION_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_futures_rs_bottom_paper_observation_v1.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 \
EXECUTION_ENABLED=0 \
REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_futures_rs_bottom_paper_observation_v1.py | tee "$out"

grep -q "VERDICT=FUTURES_RS_BOTTOM_PAPER_OBSERVATION_READY" "$out"
grep -q "TEST_FUTURES_RS_BOTTOM_PAPER_OBSERVATION_V1_OK" "$out"
grep -q "db_update=1" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"
grep -q "runtime_allow_trading=0" "$out"
grep -q "execution_enabled=0" "$out"
grep -q "real_trading_enabled=0" "$out"

psql "$DATABASE_URL" -c "
select
  selection,
  filter_name,
  status,
  count(*) as rows,
  round(avg(return_pct), 6) as avg_return_pct
from analytics_futures_rs_bottom_paper_observation_v1
group by selection, filter_name, status
order by selection, filter_name, status;
"

echo "VERDICT=FUTURES_RS_BOTTOM_PAPER_OBSERVATION_TEST_OK"
echo "TEST_FUTURES_RS_BOTTOM_PAPER_OBSERVATION_V1_OK"
