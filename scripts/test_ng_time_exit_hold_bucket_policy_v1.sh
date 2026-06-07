#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 -m py_compile src/finam_core/governance/ng_time_exit_hold_bucket_policy_v1.py

python3 - <<'PY'
from finam_core.governance.ng_time_exit_hold_bucket_policy_v1 import (
    NgTimeExitHoldBucketPolicyV1,
)

p = NgTimeExitHoldBucketPolicyV1()

cases = [
    dict(root_symbol="BR", exit_reason="time_exit", hold_seconds=1800, unrealized_pnl=-1, allowed=True),
    dict(root_symbol="NG", exit_reason="stop_loss_long", hold_seconds=1800, unrealized_pnl=-1, allowed=True),
    dict(root_symbol="NG", exit_reason="time_exit", hold_seconds=1800, unrealized_pnl=0, allowed=True),
    dict(root_symbol="NG", exit_reason="time_exit", hold_seconds=1800, unrealized_pnl=0.1, allowed=True),
    dict(root_symbol="NG", exit_reason="time_exit", hold_seconds=3599, unrealized_pnl=-0.01, allowed=False),
    dict(root_symbol="NG", exit_reason="time_exit", hold_seconds=3600, unrealized_pnl=-0.01, allowed=True),
    dict(root_symbol="NG", exit_reason="time_exit", hold_seconds=7200, unrealized_pnl=-0.01, allowed=True),
]

for c in cases:
    expected = c.pop("allowed")
    d = p.evaluate(**c)
    print(
        "NG_TIME_EXIT_HOLD_BUCKET_POLICY_ROW "
        f"root={c['root_symbol']} reason={c['exit_reason']} "
        f"hold_seconds={c['hold_seconds']} pnl={c['unrealized_pnl']} "
        f"allowed={int(d.allowed)} action={d.action} policy_reason={d.reason}"
    )
    assert d.allowed is expected

print("NG_TIME_EXIT_HOLD_BUCKET_POLICY_V1_OK")
PY

echo TEST_NG_TIME_EXIT_HOLD_BUCKET_POLICY_V1_OK
