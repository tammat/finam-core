#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_usdrub_shadow_reject_registry_v1.py

python3 src/scripts/runtime/build_usdrub_shadow_reject_registry_v1.py \
  | tee /tmp/usdrub_shadow_reject_registry_v1.log

grep -q "USDRUB SHADOW REJECT REGISTRY V1" /tmp/usdrub_shadow_reject_registry_v1.log
grep -q "REGISTRY_ROW symbol=USDRUBF@RTSX status=REJECTED" /tmp/usdrub_shadow_reject_registry_v1.log
grep -q "reason=loss_tail_filter_unstable" /tmp/usdrub_shadow_reject_registry_v1.log
grep -q "runtime_allowed=0" /tmp/usdrub_shadow_reject_registry_v1.log
grep -q "execution_enabled=0" /tmp/usdrub_shadow_reject_registry_v1.log
grep -q "USDRUB_SHADOW_REJECT_REGISTRY_V1_OK" /tmp/usdrub_shadow_reject_registry_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    status,
    reason,
    runtime_allowed,
    execution_enabled
FROM runtime_candidate_registry
WHERE symbol='USDRUBF@RTSX';
" | tee /tmp/usdrub_shadow_reject_registry_db_v1.log

grep -q "USDRUBF@RTSX" /tmp/usdrub_shadow_reject_registry_db_v1.log
grep -q "REJECTED" /tmp/usdrub_shadow_reject_registry_db_v1.log
grep -q "loss_tail_filter_unstable" /tmp/usdrub_shadow_reject_registry_db_v1.log
grep -q " f " /tmp/usdrub_shadow_reject_registry_db_v1.log

echo TEST_USDRUB_SHADOW_REJECT_REGISTRY_V1_OK
