#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_trusted_candidate_discovery_v1.py

python3 \
  src/scripts/research/build_trusted_candidate_discovery_v1.py \
  | tee /tmp/trusted_candidate_discovery_v1.log

grep -q "TRUSTED CANDIDATE DISCOVERY V1" \
  /tmp/trusted_candidate_discovery_v1.log

grep -q "TRUSTED_CANDIDATE_DISCOVERY_SUMMARY" \
  /tmp/trusted_candidate_discovery_v1.log

grep -q "TRUSTED_CANDIDATE_DISCOVERY_V1_OK" \
  /tmp/trusted_candidate_discovery_v1.log

psql "$DATABASE_URL" -c "
select count(*) unsafe_rows
from trusted_candidate_discovery_v1
where coalesce(runtime_allowed,false)=true
   or coalesce(execution_enabled,false)=true;
"

echo TEST_TRUSTED_CANDIDATE_DISCOVERY_V1_OK
