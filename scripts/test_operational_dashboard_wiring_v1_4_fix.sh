#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPERATIONAL DASHBOARD WIRING V1_4 FIX ==="

python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py
python3 -m py_compile src/scripts/research/wire_operational_dashboard_v1_4.py

grep -q "_clean_operational_positions_context_v1()" src/ui/readonly_runtime_dashboard_v1.py
grep -q "OPERATIONAL_DASHBOARD_CONTEXT_V1_4" src/ui/readonly_runtime_dashboard_v1.py
grep -q "OPERATIONAL_DASHBOARD_WIRING_V1" src/ui/templates/v3_dashboard.html

echo "runtime_allow=0"
echo "execution_enabled=0"

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
echo "=== SERVICE RESTART SKIPPED IN TEST ==="
echo "Restart dashboard manually if HTTP check serves stale HTML."

echo
echo "=== HTTP CHECK ==="
curl -fsS http://127.0.0.1:8088/ \
  | tee /tmp/operational_dashboard_home_v1_4_fix.html \
  | grep -q "Операционное состояние paper-позиций"

echo TEST_OPERATIONAL_DASHBOARD_WIRING_V1_4_FIX_OK
