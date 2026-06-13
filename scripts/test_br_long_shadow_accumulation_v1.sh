#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/br_long_shadow_accumulator_v1.py \
  src/scripts/analytics/build_br_long_shadow_report_v1.py

python3 - <<'PY'
from decimal import Decimal
from finam_core.governance.br_long_governance_v1 import BrLongGovernanceV1
from finam_core.governance.br_long_shadow_accumulator_v1 import (
    BrLongShadowAccumulatorV1,
    BrLongShadowEventV1,
)

governance = BrLongGovernanceV1(mode="shadow")
decision = governance.evaluate(symbol="BRN6@RTSX", side="BUY")

acc = BrLongShadowAccumulatorV1()
acc.record(
    BrLongShadowEventV1(
        symbol=decision.symbol,
        side=decision.side,
        strategy="TEST_BR_LONG_SHADOW",
        signal_id="test-br-long-shadow-v1",
        price=Decimal("95.50"),
        quantity=Decimal("1"),
        mode=decision.mode,
        allowed=decision.allowed,
        shadow_logged=decision.shadow_logged,
        reason=decision.reason,
    )
)

print("INSERT_OK")
PY

python3 src/scripts/analytics/build_br_long_shadow_report_v1.py | \
  tee /tmp/br_long_shadow_report_v1.log

grep -q "BR LONG SHADOW REPORT V1" /tmp/br_long_shadow_report_v1.log
grep -q "TABLE_EXISTS=1" /tmp/br_long_shadow_report_v1.log
grep -q "TOTAL_ROWS=" /tmp/br_long_shadow_report_v1.log
grep -q "signal_id=test-br-long-shadow-v1" /tmp/br_long_shadow_report_v1.log
grep -q "VERDICT=OK" /tmp/br_long_shadow_report_v1.log

psql "$DATABASE_URL" -c "
delete from research_br_long_shadow_signals
where signal_id='test-br-long-shadow-v1';
"

echo BR_LONG_SHADOW_ACCUMULATION_V1_OK
