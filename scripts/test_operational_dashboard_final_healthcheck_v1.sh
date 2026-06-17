#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPERATIONAL DASHBOARD FINAL HEALTHCHECK V1 ==="

python3 -m py_compile src/scripts/research/build_operational_dashboard_final_healthcheck_v1.py
python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py
python3 -m py_compile src/scripts/research/build_clean_operational_position_metrics_view_v1.py
python3 -m py_compile src/scripts/research/build_clean_operational_position_view_v1.py

echo
echo "=== 1. REBUILD DB VIEWS ==="
python3 src/scripts/research/build_clean_operational_position_view_v1.py \
  | tee /tmp/final_healthcheck_clean_operational_position_view_v1.log

python3 src/scripts/research/build_clean_operational_position_metrics_view_v1.py \
  | tee /tmp/final_healthcheck_clean_operational_position_metrics_v1.log

grep -q "CLEAN_OPERATIONAL_POSITION_VIEW_V1_OK" /tmp/final_healthcheck_clean_operational_position_view_v1.log
grep -q "CLEAN_OPERATIONAL_POSITION_METRICS_VIEW_V1_OK" /tmp/final_healthcheck_clean_operational_position_metrics_v1.log

echo
echo "=== 2. PYTHON HEALTHCHECK ==="
python3 src/scripts/research/build_operational_dashboard_final_healthcheck_v1.py \
  | tee /tmp/operational_dashboard_final_healthcheck_v1.log

grep -q "OPERATIONAL_DASHBOARD_FINAL_HEALTHCHECK_V1_OK" /tmp/operational_dashboard_final_healthcheck_v1.log
grep -q "VERDICT=OPERATIONAL_DASHBOARD_FINAL_HEALTHCHECK_OK" /tmp/operational_dashboard_final_healthcheck_v1.log
grep -q "runtime_allow=0" /tmp/operational_dashboard_final_healthcheck_v1.log
grep -q "execution_enabled=0" /tmp/operational_dashboard_final_healthcheck_v1.log
grep -q "DB_VIEW_ROW" /tmp/operational_dashboard_final_healthcheck_v1.log
grep -q "DB_METRICS_ROW" /tmp/operational_dashboard_final_healthcheck_v1.log
grep -q "JINJA_RENDER_OK" /tmp/operational_dashboard_final_healthcheck_v1.log

echo
echo "=== 3. SERVICE CHECK ==="
systemctl is-active --quiet finam-core-ui-readonly.service
systemctl status finam-core-ui-readonly.service --no-pager | head -30

echo
echo "=== 4. RESTART READONLY UI ==="
sudo systemctl restart finam-core-ui-readonly.service

echo
echo "=== 5. WAIT FOR 8088 ==="
ready=0
for i in $(seq 1 20); do
  if curl -fss http://127.0.0.1:8088/ >/tmp/operational_dashboard_final_root_v1.html; then
    ready=1
    echo "8088_READY attempt=${i}"
    break
  fi
  sleep 1
done

if [ "${ready}" != "1" ]; then
  echo "FAIL: 8088 did not become ready after restart"
  exit 1
fi

echo
echo "=== 6. HTTP ROOT/V3 CHECK ==="
grep -q "Операционное состояние paper-позиций" /tmp/operational_dashboard_final_root_v1.html
grep -q "Текущих paper-позиций" /tmp/operational_dashboard_final_root_v1.html
grep -q "Текущий net qty" /tmp/operational_dashboard_final_root_v1.html

curl -fss http://127.0.0.1:8088/v3 \
  | tee /tmp/operational_dashboard_final_v3_v1.html \
  | grep -q "Карантин"

grep -q "Clean V3 flat" /tmp/operational_dashboard_final_v3_v1.html

echo
echo "=== 7. SQL FINAL CHECK ==="
psql "$DATABASE_URL" -c "
select *
from clean_operational_position_metrics_v1;
"

echo TEST_OPERATIONAL_DASHBOARD_FINAL_HEALTHCHECK_V1_OK
