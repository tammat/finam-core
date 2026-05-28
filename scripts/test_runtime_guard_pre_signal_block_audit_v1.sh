#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

echo "TEST_RUNTIME_GUARD_PRE_SIGNAL_BLOCK_AUDIT_V1_START"

python -m py_compile \
  src/finam_core/analytics/runtime_guard_pre_signal_block_audit_v1.py

python - <<'PY'
from finam_core.analytics.runtime_guard_pre_signal_block_audit_v1 import (
    RuntimeGuardPreSignalBlockAuditV1,
)

audit = RuntimeGuardPreSignalBlockAuditV1()
audit.migrate()

audit.save(
    symbol="BRN6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    block_type="VOL_LOW_BLOCK",
    block_reason="br_volatility_too_low",
    price=94.88,
    atr=0.1,
    atr_pct=0.001054,
    threshold=0.0012,
    regime="range",
    trend="flat",
    volatility="normal",
    payload={"test": True},
)

print("RUNTIME_GUARD_PRE_SIGNAL_BLOCK_AUDIT_V1_PY_OK")
PY

psql "$DATABASE_URL" -c "
select
  symbol,
  strategy,
  timeframe,
  block_type,
  block_reason,
  price,
  atr,
  atr_pct,
  threshold
from runtime_guard_pre_signal_block_audit_v1
where payload->>'test' = 'true'
order by ts desc
limit 1;
"

echo "TEST_RUNTIME_GUARD_PRE_SIGNAL_BLOCK_AUDIT_V1_OK"
