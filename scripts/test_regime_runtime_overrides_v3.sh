#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/regime_runtime_override.py \
  src/scripts/runtime/build_regime_runtime_overrides.py

python - <<'PY'
from finam_core.runtime.regime_runtime_override import build_regime_runtime_override

block = build_regime_runtime_override(
    recommendation="BLOCKED|REGIME_BLOCK",
    score=0,
    confidence=0,
)
assert block.runtime_action == "BLOCK"
assert block.max_position_size == 0.0
assert block.risk_multiplier == 0.0

watch = build_regime_runtime_override(
    recommendation="RESEARCH_ONLY|REGIME_WATCH",
    score=0.2,
    confidence=0.2,
)
assert watch.runtime_action == "WATCH"
assert watch.risk_multiplier == 0.5

low_sample = build_regime_runtime_override(
    recommendation="PAPER_ENABLED|CTX_LOW_SAMPLE",
    score=0.5,
    confidence=0.5,
)
assert low_sample.runtime_action == "WATCH"
assert low_sample.stop_take_profile == "research_only"

print("RUNTIME_REGIME_OVERRIDES_V3_UNIT_OK")
PY

grep -q "runtime_regime_overrides" scripts/migrate_regime_runtime_overrides_v3.sh
grep -q "RUNTIME_REGIME_OVERRIDES_V3_OK" src/scripts/runtime/build_regime_runtime_overrides.py

echo "RUNTIME_REGIME_OVERRIDES_V3_TEST_OK"
