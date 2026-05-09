#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.risk.margin_calculator import MarginCalculator

class FakeRepo:
    def get_by_symbol(self, symbol):
        if symbol == "BRM6@RTSX":
            return {
                "symbol": "BRM6@RTSX",
                "initial_margin": 25000.0,
                "maintenance_margin": 22000.0,
                "currency": "RUB",
            }
        return None

calc = MarginCalculator(FakeRepo())

m = calc.calculate(symbol="BRM6@RTSX", qty=-2)
assert m.initial_margin == 25000.0, m
assert m.required_initial_margin == 50000.0, m
assert m.required_maintenance_margin == 44000.0, m

z = calc.calculate(symbol="UNKNOWN", qty=3)
assert z.required_initial_margin == 0.0, z

print("MARGIN_CALCULATOR_OK")
PY
