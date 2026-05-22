#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/exit_alpha_policy.py \
  src/scripts/build_exit_alpha_policy.py

python - <<'PY'
from finam_core.research.exit_alpha_policy import build_exit_alpha_policy

p = build_exit_alpha_policy(
    strategy="br_conservative_breakout",
    timeframe="m5",
    profit_factor=0.92,
    expectancy=-0.23,
    volatility_state="high",
)

assert p.strategy == "BR_CONSERVATIVE_BREAKOUT"
assert p.timeframe == "M5"
assert p.policy_name == "DEFENSIVE_EXIT_ALPHA_V1"
assert p.max_bars_held <= 10

print("TEST_EXIT_ALPHA_POLICY_OK")
PY
