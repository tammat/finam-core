#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/execution/trailing_exit_policy.py \
  src/scripts/run_trailing_exit_supervisor.py

python - <<'PY'
from finam_core.execution.trailing_exit_policy import TrailingExitPolicy

p = TrailingExitPolicy()
d = p.decide(avg_price=100, current_price=110, trail_pct=0.01)

assert d.exit_required is False
assert d.stop_price == 108.9

print("OK: trailing exit policy")
PY

grep -q "TRAILING_EXIT_INTENT_CREATED" src/scripts/run_trailing_exit_supervisor.py
grep -q "trailing_exit_market_sell" src/scripts/run_trailing_exit_supervisor.py

echo "OK: trailing exit supervisor"
