#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export BR_LONG_MODE=shadow

python3 -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/governance/br_long_governance_v1.py \
  src/finam_core/governance/br_long_shadow_accumulator_v1.py

python3 - <<'PY' | tee /tmp/br_long_shadow_pipeline_hook_v1.log
from finam_core.pipelines.paper_pipeline import _br_long_shadow_pipeline_hook_v1

print("=== BR LONG SHADOW PIPELINE HOOK V1 ===")

allowed_br_buy = _br_long_shadow_pipeline_hook_v1(
    symbol="BRN6@RTSX",
    side="BUY",
    strategy="TEST_BR_LONG_PIPELINE_HOOK",
    signal_id="test-br-long-pipeline-hook-v1",
    price="95.50",
    quantity="1",
)

allowed_br_sell = _br_long_shadow_pipeline_hook_v1(
    symbol="BRN6@RTSX",
    side="SELL",
    strategy="TEST_BR_LONG_PIPELINE_HOOK",
    signal_id="test-br-sell-pipeline-hook-v1",
    price="95.50",
    quantity="1",
)

allowed_ng_buy = _br_long_shadow_pipeline_hook_v1(
    symbol="NGN6@RTSX",
    side="BUY",
    strategy="TEST_NG_PIPELINE_HOOK",
    signal_id="test-ng-buy-pipeline-hook-v1",
    price="2.50",
    quantity="1",
)

print(f"ASSERT_BR_BUY_ALLOWED={int(allowed_br_buy)}")
print(f"ASSERT_BR_SELL_ALLOWED={int(allowed_br_sell)}")
print(f"ASSERT_NG_BUY_ALLOWED={int(allowed_ng_buy)}")

if allowed_br_buy:
    raise SystemExit("BR_BUY_SHOULD_BE_BLOCKED_IN_SHADOW")
if not allowed_br_sell:
    raise SystemExit("BR_SELL_SHOULD_BE_ALLOWED")
if not allowed_ng_buy:
    raise SystemExit("NG_BUY_SHOULD_BE_ALLOWED")

print("PY_ASSERTIONS_OK")
PY

grep -q "BR LONG SHADOW PIPELINE HOOK V1" /tmp/br_long_shadow_pipeline_hook_v1.log
grep -q "PIPE_BR_LONG_GOVERNANCE_V1 symbol=BRN6@RTSX side=BUY mode=shadow allowed=0 shadow_logged=1" /tmp/br_long_shadow_pipeline_hook_v1.log
grep -q "PIPE_BR_LONG_SHADOW_ACCUMULATION_OK symbol=BRN6@RTSX side=BUY" /tmp/br_long_shadow_pipeline_hook_v1.log
grep -q "ASSERT_BR_BUY_ALLOWED=0" /tmp/br_long_shadow_pipeline_hook_v1.log
grep -q "ASSERT_BR_SELL_ALLOWED=1" /tmp/br_long_shadow_pipeline_hook_v1.log
grep -q "ASSERT_NG_BUY_ALLOWED=1" /tmp/br_long_shadow_pipeline_hook_v1.log
grep -q "PY_ASSERTIONS_OK" /tmp/br_long_shadow_pipeline_hook_v1.log

psql "$DATABASE_URL" -c "
select
  symbol,
  side,
  strategy,
  signal_id,
  mode,
  allowed,
  shadow_logged,
  reason
from research_br_long_shadow_signals
where signal_id='test-br-long-pipeline-hook-v1';
"

psql "$DATABASE_URL" -c "
delete from research_br_long_shadow_signals
where signal_id in (
  'test-br-long-pipeline-hook-v1',
  'test-br-sell-pipeline-hook-v1',
  'test-ng-buy-pipeline-hook-v1'
);
"

echo BR_LONG_SHADOW_PIPELINE_HOOK_V1_OK
