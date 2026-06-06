#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/br_short_shadow_policy_v1.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "br_short_shadow_pipeline_hook_v1_call" \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "PIPE_BR_SHORT_SHADOW_POLICY_V1" \
  src/finam_core/pipelines/paper_pipeline.py

python3 - <<'PY'
from finam_core.pipelines.paper_pipeline import _br_short_shadow_pipeline_hook_v1

ok = _br_short_shadow_pipeline_hook_v1(
    symbol="BRN6@RTSX",
    side="SELL",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    current_position=0.0,
    signal_id="test-br-short-shadow-v1",
    price=93.5,
    quantity=1.0,
)

assert ok is True
print("PY_ASSERTIONS_OK")
PY

echo BR_SHORT_SHADOW_PIPELINE_HOOK_V1_OK
