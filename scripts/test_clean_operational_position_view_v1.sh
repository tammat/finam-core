#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST CLEAN OPERATIONAL POSITION VIEW V1 ==="

python3 -m py_compile src/scripts/research/build_clean_operational_position_view_v1.py

python3 src/scripts/research/build_clean_operational_position_view_v1.py \
  | tee /tmp/clean_operational_position_view_v1.log

grep -q "CLEAN_OPERATIONAL_POSITION_VIEW_V1_OK" /tmp/clean_operational_position_view_v1.log
grep -q "VERDICT=CLEAN_OPERATIONAL_POSITION_VIEW_READY" /tmp/clean_operational_position_view_v1.log
grep -q "runtime_allow=0" /tmp/clean_operational_position_view_v1.log
grep -q "execution_enabled=0" /tmp/clean_operational_position_view_v1.log
grep -q "brn6_open_ok=1" /tmp/clean_operational_position_view_v1.log
grep -q "brm6_excluded_ok=1" /tmp/clean_operational_position_view_v1.log
grep -q "usdrubf_quarantine_ok=1" /tmp/clean_operational_position_view_v1.log
grep -q "ngq6_flat_ok=1" /tmp/clean_operational_position_view_v1.log

echo
echo "=== SQL VIEW CHECK ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    net_qty,
    full_chains,
    round(v3_pnl,6) as pnl,
    operational_status,
    is_current_operational_position,
    include_in_clean_operational_view
from clean_operational_position_view_v1
order by operational_status, symbol, strategy, timeframe;
"

echo TEST_CLEAN_OPERATIONAL_POSITION_VIEW_V1_OK
