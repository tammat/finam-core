#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NGQ6 RUNTIME ALLOCATOR PERSISTENCE V1 ==="
echo "mode=static_and_db_check"
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile src/finam_core/runtime/runtime_universe_allocator.py

grep -q "manual_forward_accumulation_seed" src/finam_core/runtime/runtime_universe_allocator.py
grep -q "manual_forward_accumulation" src/finam_core/runtime/runtime_universe_allocator.py

bash scripts/test_ngq6_runtime_universe_seed_v1.sh >/tmp/ngq6_seed_persistence_v1.log

before_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from runtime_active_universe
where symbol='NGQ6@RTSX'
  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
  and timeframe='M1'
  and source='manual_forward_accumulation_seed'
  and is_enabled=true;
")

echo "ngq6_seed_rows_before_allocator=${before_rows}"

if [ "${before_rows}" != "1" ]; then
  echo "FAIL: NGQ6 seed missing before allocator"
  exit 1
fi

echo "NGQ6_RUNTIME_ALLOCATOR_PERSISTENCE_V1_OK"
