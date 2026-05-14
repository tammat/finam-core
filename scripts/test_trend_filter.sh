#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/strategy/trend_filter.py

python - <<'PY'
from finam_core.strategy.trend_filter import TrendFilter

f = TrendFilter()

d = f.check(expected="SELL", actual="BUY")
assert d.allowed is False
assert d.reason == "trend_mismatch"

d = f.check(expected="BUY", actual="BUY")
assert d.allowed is True

d = f.check(expected=None, actual="BUY")
assert d.allowed is True

print("OK: TrendFilter")
PY
