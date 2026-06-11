#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_runtime_candidate_registry_v1.py
python3 -m py_compile src/ui/readonly_runtime_dashboard_v1.py

python3 src/scripts/runtime/build_runtime_candidate_registry_v1.py \
  | tee /tmp/runtime_candidate_registry_v1.log

grep -q "RUNTIME_CANDIDATE_REGISTRY_V1_OK" /tmp/runtime_candidate_registry_v1.log
grep -q "symbol=GDU6@RTSX" /tmp/runtime_candidate_registry_v1.log
grep -q "status=WATCH_RUNTIME" /tmp/runtime_candidate_registry_v1.log
grep -q "runtime_allowed=0" /tmp/runtime_candidate_registry_v1.log
grep -q "execution_enabled=0" /tmp/runtime_candidate_registry_v1.log

grep -q "table-wrap" src/ui/templates/base.html
grep -q "reason-cell" src/ui/templates/base.html
grep -q "table class=\"wide\"" src/ui/templates/instruments.html
grep -q "table class=\"wide\"" src/ui/templates/runtime_candidates.html

psql "$DATABASE_URL" -P pager=off -c "
SELECT symbol, status, runtime_allowed, execution_enabled
FROM runtime_candidate_registry
ORDER BY symbol;
"

echo TEST_RUNTIME_CANDIDATE_REGISTRY_V1_OK
