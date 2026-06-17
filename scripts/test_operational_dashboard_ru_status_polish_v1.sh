#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPERATIONAL DASHBOARD RU STATUS POLISH V1 ==="

python3 -m py_compile src/scripts/research/polish_operational_dashboard_ru_status_v1.py

python3 src/scripts/research/polish_operational_dashboard_ru_status_v1.py \
  | tee /tmp/operational_dashboard_ru_status_polish_v1.log

grep -q "OPERATIONAL_DASHBOARD_RU_STATUS_POLISH_V1_OK" /tmp/operational_dashboard_ru_status_polish_v1.log
grep -q "runtime_allow=0" /tmp/operational_dashboard_ru_status_polish_v1.log
grep -q "execution_enabled=0" /tmp/operational_dashboard_ru_status_polish_v1.log

grep -q "Текущая paper-позиция" src/ui/templates/v3_dashboard.html
grep -q "Clean V3 без открытой позиции" src/ui/templates/v3_dashboard.html
grep -q "Карантин" src/ui/templates/v3_dashboard.html
grep -q "Исключено из operational state" src/ui/templates/v3_dashboard.html

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

echo
echo "=== SERVICE RESTART ==="
sudo systemctl restart finam-core-ui-readonly.service

echo
echo "=== WAIT FOR 8088 ==="
ready=0
for i in $(seq 1 20); do
  if curl -fss http://127.0.0.1:8088/ >/tmp/operational_dashboard_ru_status_root_v1.html; then
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

grep -q "Текущая paper-позиция" /tmp/operational_dashboard_ru_status_root_v1.html

echo
echo "=== HTTP CHECK V3 ==="
curl -fsS http://127.0.0.1:8088/v3 \
  | tee /tmp/operational_dashboard_ru_status_v3_v1.html \
  | grep -q "Карантин"

echo TEST_OPERATIONAL_DASHBOARD_RU_STATUS_POLISH_V1_OK
