#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_quarantine_reconstruction_artifacts_v1.py

python3 \
  src/scripts/research/build_quarantine_reconstruction_artifacts_v1.py \
  | tee /tmp/quarantine_reconstruction_artifacts_v1.log

grep -q "QUARANTINE RECONSTRUCTION ARTIFACTS V1" \
  /tmp/quarantine_reconstruction_artifacts_v1.log

grep -q "QUARANTINE_SUMMARY" \
  /tmp/quarantine_reconstruction_artifacts_v1.log

grep -q "QUARANTINE_RECONSTRUCTION_ARTIFACTS_V1_OK" \
  /tmp/quarantine_reconstruction_artifacts_v1.log

psql "$DATABASE_URL" -c "
select count(*) unsafe_rows
from quarantine_reconstruction_artifacts_v1
where runtime_allowed=true
   or execution_enabled=true;
"

echo TEST_QUARANTINE_RECONSTRUCTION_ARTIFACTS_V1_OK
