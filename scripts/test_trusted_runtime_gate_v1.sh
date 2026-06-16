#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/runtime/build_trusted_runtime_gate_v1.py

python3 \
  src/scripts/runtime/build_trusted_runtime_gate_v1.py \
  | tee /tmp/trusted_runtime_gate_v1.log

grep -q "TRUSTED RUNTIME GATE V1" \
  /tmp/trusted_runtime_gate_v1.log

grep -q "TRUSTED_RUNTIME_GATE_SUMMARY" \
  /tmp/trusted_runtime_gate_v1.log

grep -q "TRUSTED_RUNTIME_GATE_V1_OK" \
  /tmp/trusted_runtime_gate_v1.log

psql "$DATABASE_URL" -c "
select count(*) unsafe_rows
from trusted_runtime_gate_v1
where runtime_allowed=true
   or execution_enabled=true
   or allow_real_runtime=true;
"

echo TEST_TRUSTED_RUNTIME_GATE_V1_OK
