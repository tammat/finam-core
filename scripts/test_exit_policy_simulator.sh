#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.exit_policy_simulator import (
    ExitPolicyCandidate,
    ExitPolicyInput,
    simulate_exit_policy,
)

samples = [
    ExitPolicyInput(pnl=5.0, mae=-1.0, mfe=10.0),
    ExitPolicyInput(pnl=-3.0, mae=-5.0, mfe=2.0),
    ExitPolicyInput(pnl=4.0, mae=-2.0, mfe=8.0),
]

candidate = ExitPolicyCandidate(
    name="take6_stop4",
    take_distance=6.0,
    stop_distance=-4.0,
)

result = simulate_exit_policy(samples, candidate)

assert result.policy_name == "take6_stop4"
assert result.simulated_trades == 3
assert result.simulated_net_pnl == 8.0
assert result.simulated_wins == 2
assert result.simulated_losses == 1
assert result.simulated_profit_factor == 3.0

print("TEST_EXIT_POLICY_SIMULATOR_OK")
PY
