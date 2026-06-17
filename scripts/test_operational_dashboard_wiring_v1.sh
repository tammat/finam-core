#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST OPERATIONAL DASHBOARD WIRING V1 ==="

python3 -m py_compile src/scripts/research/wire_operational_dashboard_v1.py
python3 src/scripts/research/wire_operational_dashboard_v1.py \
  | tee /tmp/operational_dashboard_wiring_v1.log

grep -q "OPERATIONAL_DASHBOARD_WIRING_V1_OK" /tmp/operational_dashboard_wiring_v1.log
grep -q "runtime_allow=0" /tmp/operational_dashboard_wiring_v1.log
grep -q "execution_enabled=0" /tmp/operational_dashboard_wiring_v1.log

echo
echo "=== STATIC MARKER CHECK ==="
grep -R "OPERATIONAL_DASHBOARD_WIRING_V1" -n . \
  --exclude-dir=.git \
  --exclude-dir=venv \
  --exclude-dir=.venv

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
echo "=== HTTP CHECK ==="
if command -v curl >/dev/null 2>&1; then
  curl -fsS http://127.0.0.1:8088/ \
    | tee /tmp/operational_dashboard_home_v1.html \
    | grep -q "Операционное состояние paper-позиций"
else
  echo "curl not found, skipping HTTP check"
fi

echo TEST_OPERATIONAL_DASHBOARD_WIRING_V1_OK
