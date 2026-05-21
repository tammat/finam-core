#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.exit_optimization import (
    IntrabarTradeSample,
    build_exit_optimization_profile,
)

samples = [
    IntrabarTradeSample(pnl=5.0, mae=-1.0, mfe=10.0, exit_efficiency=0.5),
    IntrabarTradeSample(pnl=3.0, mae=-2.0, mfe=8.0, exit_efficiency=0.375),
    IntrabarTradeSample(pnl=-2.0, mae=-5.0, mfe=4.0, exit_efficiency=-0.5),
    IntrabarTradeSample(pnl=7.0, mae=-1.5, mfe=12.0, exit_efficiency=0.5833333333),
    IntrabarTradeSample(pnl=-1.0, mae=-3.0, mfe=6.0, exit_efficiency=-0.1666666667),
]

profile = build_exit_optimization_profile(samples)

assert profile.trades == 5
assert profile.p50_mfe == 8.0
assert profile.p70_mfe == 9.6
assert profile.p80_mfe == 10.4
assert profile.p50_mae_abs == 2.0
assert profile.recommended_stop_50 == -2.0
assert profile.recommended_take_50 == 8.0

print("TEST_EXIT_OPTIMIZATION_OK")
PY
