#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/finam_core/governance/guard_shadow_accumulator.py

python3 - <<'PY'
from finam_core.governance.guard_shadow_accumulator import (
    GuardShadowAccumulator,
    GuardShadowEvent,
)

acc = GuardShadowAccumulator()
acc.ensure_schema()

acc.record(
    GuardShadowEvent(
        symbol="TEST@RTSX",
        strategy="TEST_STRATEGY",
        timeframe="M1",
        side="LONG",
        session_bucket="TEST_SESSION",
        classification="BLOCK_READY",
        reason="test_shadow_accumulation",
        would_block=True,
        actual_block=False,
        advisory_only=True,
        signal_id="test-shadow-accumulation-v1",
    )
)

print("GUARD_SHADOW_ACCUMULATION_RECORD_OK")
PY

psql "$DATABASE_URL" -c "
select
  symbol,
  strategy,
  timeframe,
  side,
  session_bucket,
  classification,
  reason,
  would_block,
  actual_block,
  advisory_only,
  signal_id
from guard_shadow_accumulation
where signal_id='test-shadow-accumulation-v1'
order by created_at desc
limit 1;
"

echo GUARD_SHADOW_ACCUMULATION_V1_OK
