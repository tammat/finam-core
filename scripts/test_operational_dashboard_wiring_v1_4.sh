#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPERATIONAL DASHBOARD WIRING V1_4 ==="

python3 -m py_compile src/scripts/research/wire_operational_dashboard_v1_4.py

python3 src/scripts/research/wire_operational_dashboard_v1_4.py \
  | tee /tmp/operational_dashboard_wiring_v1_4.log

grep -q "OPERATIONAL_DASHBOARD_WIRING_V1_4_OK" /tmp/operational_dashboard_wiring_v1_4.log
grep -q "FOUND_REAL_APP_FILE=.*/src/ui/readonly_runtime_dashboard_v1.py" /tmp/operational_dashboard_wiring_v1_4.log
grep -q "runtime_allow=0" /tmp/operational_dashboard_wiring_v1_4.log
grep -q "execution_enabled=0" /tmp/operational_dashboard_wiring_v1_4.log

echo
echo "=== SHOW PATCHED V3 DASHBOARD BLOCK ==="
grep -n "v3_dashboard.html\|_clean_operational_positions_context_v1\|OPERATIONAL_DASHBOARD_CONTEXT_V1_4" \
  src/ui/readonly_runtime_dashboard_v1.py

echo
echo "=== PY COMPILE REAL APP ==="
python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

echo
echo "=== SQL VIEW CHECK ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    net_qty,
    full_chains,
    round(v3_pnl::numeric,6) as pnl,
    operational_status,
    is_current_operational_position,
    include_in_clean_operational_view
from clean_operational_position_view_v1
order by operational_status, symbol, strategy, timeframe;
"

echo
echo "=== SERVICE RESTART TRY ==="
sudo systemctl restart finam-dashboard.service 2>/dev/null \
  || sudo systemctl restart finam-web.service 2>/dev/null \
  || true

echo
echo "=== HTTP CHECK ==="
if command -v curl >/dev/null 2>&1; then
  curl -fsS http://127.0.0.1:8088/ \
    | tee /tmp/operational_dashboard_home_v1_4.html \
    | grep -q "Операционное состояние paper-позиций"
else
  echo "curl not found, skipping HTTP check"
fi

echo TEST_OPERATIONAL_DASHBOARD_WIRING_V1_4_OK
