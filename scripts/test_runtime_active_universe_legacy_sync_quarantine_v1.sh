#!/usr/bin/env bash
set -euo pipefail

echo "=== RUNTIME_ACTIVE_UNIVERSE_LEGACY_SYNC_QUARANTINE_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/sync_runtime_active_universe_from_strategy_selection.py

before="$(psql "$DATABASE_URL" -At -c "
select count(*)
from runtime_active_universe
where symbol like '%@MISX'
  and is_enabled = true
  and source = 'runtime_universe_allocator_v2';
")"

python3 src/scripts/sync_runtime_active_universe_from_strategy_selection.py | tee "$out"

after="$(psql "$DATABASE_URL" -At -c "
select count(*)
from runtime_active_universe
where symbol like '%@MISX'
  and is_enabled = true
  and source = 'runtime_universe_allocator_v2';
")"

test "$before" = "$after"
test "$after" = "8"

grep -q "SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_STRATEGY_SELECTION_QUARANTINED" "$out"

echo "VERDICT=RUNTIME_ACTIVE_UNIVERSE_LEGACY_SYNC_QUARANTINE_OK"
echo "TEST_RUNTIME_ACTIVE_UNIVERSE_LEGACY_SYNC_QUARANTINE_V1_OK"
