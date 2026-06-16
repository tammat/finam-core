#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_strategy_identity_governance_v1.py
python3 src/scripts/research/build_strategy_identity_governance_v1.py | tee /tmp/strategy_identity_governance_v1.log

grep -q "STRATEGY_IDENTITY_GOVERNANCE_V1_OK" /tmp/strategy_identity_governance_v1.log
grep -q "runtime_allow=0" /tmp/strategy_identity_governance_v1.log
grep -q "execution_enabled=0" /tmp/strategy_identity_governance_v1.log

psql "$DATABASE_URL" -c "
select count(*) unsafe_rows
from strategy_identity_governance_v1
where coalesce(runtime_allowed,false)=true
   or coalesce(execution_enabled,false)=true
   or coalesce(allow_paper_signal,false)=true
   or coalesce(allow_real_suggestion,false)=true;
"

echo TEST_STRATEGY_IDENTITY_GOVERNANCE_V1_OK
