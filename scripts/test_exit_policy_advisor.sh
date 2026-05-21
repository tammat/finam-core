#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.runtime.exit_policy_advisor import ExitPolicyAdvice

advice = ExitPolicyAdvice(
    symbol="BRM6@RTSX",
    strategy="br_conservative_breakout",
    timeframe="M5",
    policy="take50_stop50",
    take_distance=0.5395,
    stop_distance=-0.4375,
    profit_factor=5.52,
    net_pnl=41.85,
    max_drawdown=-4.49,
    winrate=0.7,
)

assert advice.symbol == "BRM6@RTSX"
assert advice.policy == "take50_stop50"
assert advice.take_distance > 0
assert advice.stop_distance < 0
assert advice.source == "analytics_exit_policy_selected"

print("TEST_EXIT_POLICY_ADVISOR_OK")
PY

python -m py_compile src/finam_core/runtime/exit_policy_advisor.py
