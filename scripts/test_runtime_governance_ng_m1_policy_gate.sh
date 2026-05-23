#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/runtime_governance_engine.py \
  src/scripts/build_runtime_governance_decisions.py

grep -q "BLOCK_NG_M1_REGIME_POLICY" src/finam_core/runtime/runtime_governance_engine.py
grep -q "ng_m1_runtime_policy" src/scripts/build_runtime_governance_decisions.py
grep -q "ng_m1_policy_required" src/scripts/build_runtime_governance_decisions.py

python - <<'PY'
from finam_core.runtime.runtime_governance_engine import RuntimeGovernanceEngine, RuntimeGovernanceInput

engine = RuntimeGovernanceEngine()

d = engine.decide(RuntimeGovernanceInput(
    symbol="NGF6@RTSX",
    strategy="NG_CONSERVATIVE_BREAKOUT_M1",
    timeframe="M1",
    runtime_mode="PAPER",
    runtime_enabled=True,
    runtime_reason="ok",
    ng_m1_policy_required=True,
    ng_m1_policy_allow_runtime=False,
    ng_m1_policy_reason="ng_m1_policy_block",
))

assert d.decision == "BLOCK_NG_M1_REGIME_POLICY"
assert d.allow_runtime is False

print("TEST_RUNTIME_GOVERNANCE_NG_M1_POLICY_GATE_OK")
PY
