#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/runtime/runtime_governance_engine.py \
  src/scripts/build_runtime_governance_decisions.py

python - <<'PY'
from finam_core.runtime.runtime_governance_engine import (
    RuntimeGovernanceEngine,
    RuntimeGovernanceInput,
)

engine = RuntimeGovernanceEngine()

d1 = engine.decide(RuntimeGovernanceInput(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    runtime_mode="PAPER",
    runtime_enabled=False,
    runtime_reason="blocked_by_statistics",
))
assert d1.decision == "BLOCK_RUNTIME_SELECTION"
assert d1.allow_runtime is False

d2 = engine.decide(RuntimeGovernanceInput(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    runtime_mode="PAPER",
    runtime_enabled=True,
    runtime_reason="ok",
    event_allow_runtime=False,
    event_reason="important_event",
))
assert d2.decision == "BLOCK_EVENT_RISK"
assert d2.allow_runtime is False

d3 = engine.decide(RuntimeGovernanceInput(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    runtime_mode="PAPER",
    runtime_enabled=True,
    runtime_reason="ok",
    session_allow_runtime=False,
    session_reason="bad_session",
))
assert d3.decision == "BLOCK_SESSION_RISK"
assert d3.allow_runtime is False

d4 = engine.decide(RuntimeGovernanceInput(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    runtime_mode="PAPER",
    runtime_enabled=True,
    runtime_reason="ok",
    event_risk_multiplier=0.5,
))
assert d4.decision == "ALLOW_REDUCED_RISK"
assert d4.allow_runtime is True
assert d4.risk_multiplier == 0.5

print("TEST_RUNTIME_GOVERNANCE_ENGINE_OK")
PY
