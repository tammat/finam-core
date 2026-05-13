#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/signal_repository.py

python - <<'PY'
from finam_core.analytics.signal_repository import SignalRepository

assert SignalRepository._calc_rr(100, 95, 110) == 2.0
assert SignalRepository._calc_rr(100, 100, 110) is None
assert SignalRepository._calc_rr(None, 95, 110) is None

print("OK: SignalRepository compile and RR tests passed")
PY
