#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/finam_core/governance/time_exit_governance_v1.py

python3 - <<'PY'
from finam_core.governance.time_exit_governance_v1 import TimeExitGovernanceV1

g = TimeExitGovernanceV1(mode="shadow")

cases = [
    ("BR", "SELL", -1.0, "time_exit", False, "SHADOW_BLOCK"),
    ("BR", "SELL",  1.0, "time_exit", False, "SHADOW_BLOCK"),
    ("NG", "SELL", -1.0, "time_exit", False, "SHADOW_BLOCK"),
    ("NG", "SELL",  0.0, "time_exit", True,  "ALLOW"),
    ("NG", "SELL",  1.0, "time_exit", True,  "ALLOW"),
    ("NG", "SELL", -1.0, "stop_loss_long", True, "PASS"),
]

for root, side, pnl, reason, expected_allowed, expected_action in cases:
    d = g.evaluate(root_symbol=root, side=side, unrealized_pnl=pnl, reason=reason)
    print(
        f"TIME_EXIT_GOVERNANCE_ROW root={root} side={side} pnl={pnl} "
        f"reason={reason} allowed={int(d.allowed)} action={d.action} policy_reason={d.reason}"
    )
    assert d.allowed is expected_allowed
    assert d.action == expected_action

print("TIME_EXIT_GOVERNANCE_V1_OK")
PY

echo TEST_TIME_EXIT_GOVERNANCE_V1_OK
