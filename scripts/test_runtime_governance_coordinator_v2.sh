#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.runtime.runtime_governance_coordinator_v2 import (
    RuntimeGovernanceDecisionV2,
)

d = RuntimeGovernanceDecisionV2(
    symbol="BRM6@RTSX",
    strategy="br_conservative_breakout",
    timeframe="M5",
    mode="ADVISORY_ONLY",
    heat_status="HIGH",
    risk_multiplier=0.5,
    allow_new_entries=True,
    allow_execution=True,
    watch_only=False,
    reason="portfolio_heat_high_reduce_risk",
)

assert d.heat_status == "HIGH"
assert d.risk_multiplier == 0.5
assert d.allow_execution is True
assert d.watch_only is False

print("TEST_RUNTIME_GOVERNANCE_COORDINATOR_V2_OK")
PY

python -m py_compile src/finam_core/runtime/runtime_governance_coordinator_v2.py
