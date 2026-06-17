#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST RUNTIME OPERATIONAL GOVERNANCE ALIGNMENT V1 ==="

python3 -m py_compile src/scripts/research/build_runtime_operational_governance_alignment_v1.py
python3 -m py_compile src/scripts/research/build_clean_operational_position_view_v1.py
python3 -m py_compile src/scripts/research/build_clean_operational_position_metrics_view_v1.py

echo
echo "=== 1. REBUILD OPERATIONAL DB VIEWS ==="
python3 src/scripts/research/build_clean_operational_position_view_v1.py \
  | tee /tmp/runtime_alignment_operational_view_v1.log

python3 src/scripts/research/build_clean_operational_position_metrics_view_v1.py \
  | tee /tmp/runtime_alignment_operational_metrics_v1.log

grep -q "CLEAN_OPERATIONAL_POSITION_VIEW_V1_OK" /tmp/runtime_alignment_operational_view_v1.log
grep -q "CLEAN_OPERATIONAL_POSITION_METRICS_VIEW_V1_OK" /tmp/runtime_alignment_operational_metrics_v1.log

echo
echo "=== 2. ALIGNMENT AUDIT ==="
python3 src/scripts/research/build_runtime_operational_governance_alignment_v1.py \
  | tee /tmp/runtime_operational_governance_alignment_v1.log

grep -q "RUNTIME_OPERATIONAL_GOVERNANCE_ALIGNMENT_V1_OK" /tmp/runtime_operational_governance_alignment_v1.log
grep -q "VERDICT=RUNTIME_OPERATIONAL_GOVERNANCE_ALIGNED_READONLY" /tmp/runtime_operational_governance_alignment_v1.log
grep -q "runtime_allow=0" /tmp/runtime_operational_governance_alignment_v1.log
grep -q "execution_enabled=0" /tmp/runtime_operational_governance_alignment_v1.log
grep -q "BLOCKERS=none" /tmp/runtime_operational_governance_alignment_v1.log

echo
echo "=== 3. HARD CHECK: QUARANTINE / EXCLUDED NOT ACTIVE ==="
psql "$DATABASE_URL" -c "
select
    o.symbol,
    o.operational_status,
    r.*
from clean_operational_position_view_v1 o
left join runtime_active_universe r
  on r.symbol = o.symbol
where o.operational_status in ('QUARANTINE_CONTAMINATED_TAIL', 'EXCLUDE_HISTORICAL_TAIL');
"

echo TEST_RUNTIME_OPERATIONAL_GOVERNANCE_ALIGNMENT_V1_OK
