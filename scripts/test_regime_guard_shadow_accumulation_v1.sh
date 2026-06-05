#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/regime_guard_shadow_accumulator.py \
  src/scripts/research/build_regime_guard_shadow_report_v1.py

python3 - <<'PY'
from finam_core.governance.regime_guard_shadow_accumulator import RegimeGuardShadowAccumulator

acc = RegimeGuardShadowAccumulator()
acc.record(
    symbol="TEST@RTSX",
    signal_id="test-regime-guard-shadow-v1",
    strategy="TEST_STRATEGY",
    regime_key="BR=COMPRESSION|NG=COMPRESSION|USD=COMPRESSION",
    classification="BLOCK_CANDIDATE",
    would_block=True,
    reason="test_shadow_accumulation",
)

print("INSERT_OK")
PY

psql "$DATABASE_URL" -c "
select
  symbol,
  signal_id,
  strategy,
  regime_key,
  classification,
  would_block,
  actual_block,
  advisory_only,
  reason
from research_regime_guard_shadow
where signal_id='test-regime-guard-shadow-v1';
"

python3 src/scripts/research/build_regime_guard_shadow_report_v1.py \
  --since "24 hours" | tee /tmp/regime_guard_shadow_report_v1.log

grep -q "REGIME GUARD SHADOW REPORT V1" /tmp/regime_guard_shadow_report_v1.log
grep -q "TABLE_EXISTS=1" /tmp/regime_guard_shadow_report_v1.log
grep -q "TOTAL_ROWS=" /tmp/regime_guard_shadow_report_v1.log
grep -q "VERDICT=OK" /tmp/regime_guard_shadow_report_v1.log

psql "$DATABASE_URL" -c "
delete from research_regime_guard_shadow
where signal_id='test-regime-guard-shadow-v1';
"

echo REGIME_GUARD_SHADOW_ACCUMULATION_V1_OK
