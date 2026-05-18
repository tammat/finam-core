#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/portfolio_heat_risk_gate.py \
  src/scripts/analyze_watch_candidates_runtime.py

python - <<'PY'
from finam_core.runtime.portfolio_heat_risk_gate import PortfolioHeatRiskGate


class Cursor:
    def __init__(self, row):
        self.row = row

    def execute(self, *_args, **_kwargs):
        pass

    def fetchone(self):
        return self.row

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class Conn:
    def __init__(self, row):
        self.row = row

    def cursor(self):
        return Cursor(self.row)


assert PortfolioHeatRiskGate(Conn((10, 0, 1000))).check().allowed is True
assert PortfolioHeatRiskGate(Conn((80, 0, 1000))).check().allowed is False
assert PortfolioHeatRiskGate(Conn((10, -20000, 1000))).check().allowed is False
assert PortfolioHeatRiskGate(Conn((10, 0, 999999))).check().allowed is False
assert PortfolioHeatRiskGate(Conn(None)).check().allowed is True

print("OK: portfolio heat risk gate")
PY

echo "OK: portfolio heat risk gate compile"
