#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/runtime/sync_runtime_active_universe_from_trusted_gate_v1.py

python3 \
  src/scripts/runtime/sync_runtime_active_universe_from_trusted_gate_v1.py \
  | tee /tmp/wire_trusted_gate_to_runtime_active_universe_v1.log

grep -q "WIRE TRUSTED GATE TO RUNTIME ACTIVE UNIVERSE V1" \
  /tmp/wire_trusted_gate_to_runtime_active_universe_v1.log

grep -q "TRUSTED_GATE_RUNTIME_UNIVERSE_SUMMARY" \
  /tmp/wire_trusted_gate_to_runtime_active_universe_v1.log

grep -q "WIRE_TRUSTED_GATE_TO_RUNTIME_ACTIVE_UNIVERSE_V1_OK" \
  /tmp/wire_trusted_gate_to_runtime_active_universe_v1.log

active_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from runtime_active_universe
where coalesce(is_enabled,true)=true;
")

echo "active_runtime_universe_rows=${active_rows}"

if [ "${active_rows}" != "0" ]; then
  echo "FAIL: runtime_active_universe still has enabled rows"
  exit 1
fi

echo TEST_WIRE_TRUSTED_GATE_TO_RUNTIME_ACTIVE_UNIVERSE_V1_OK
