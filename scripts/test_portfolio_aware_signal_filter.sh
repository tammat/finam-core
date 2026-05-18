#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/portfolio_aware_signal_filter.py \
  src/scripts/analyze_watch_candidates_runtime.py

python - <<'PY'
from finam_core.runtime.portfolio_aware_signal_filter import PortfolioAwareSignalFilter


class Cursor:
    def __init__(self, values):
        self.values = list(values)

    def execute(self, *_args, **_kwargs):
        pass

    def fetchone(self):
        return (self.values.pop(0),)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class Conn:
    def __init__(self, values):
        self.values = values

    def cursor(self):
        return Cursor(self.values)


assert PortfolioAwareSignalFilter(Conn([0, 0])).check(symbol="SBER@MISX").allowed is True
assert PortfolioAwareSignalFilter(Conn([1])).check(symbol="SBER@MISX").allowed is False
assert PortfolioAwareSignalFilter(Conn([0, 5])).check(symbol="SBER@MISX", max_active_signals=5).allowed is False

print("OK: portfolio aware signal filter")
PY

echo "OK: portfolio aware signal filter compile"
