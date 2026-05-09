#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.analytics.fee_calculator import FeeCalculator

class FakeRepo:
    def get_profile(self, *, asset_class, symbol):
        if asset_class == "FUTURES":
            return {
                "broker_fee_per_contract": 1.0,
                "exchange_fee_per_contract": 0.5,
                "clearing_fee_per_contract": 0.25,
                "broker_fee_pct": 0.0,
                "exchange_fee_pct": 0.0,
                "min_fee": 0.0,
            }
        return {
            "broker_fee_per_contract": 0.0,
            "exchange_fee_per_contract": 0.0,
            "clearing_fee_per_contract": 0.0,
            "broker_fee_pct": 0.0005,
            "exchange_fee_pct": 0.0001,
            "min_fee": 1.0,
        }

calc = FeeCalculator(FakeRepo())

f = calc.calculate(symbol="BRM6@RTSX", asset_class="FUTURES", qty=2, price=80, side="BUY")
assert f.broker_fee == 2.0
assert f.exchange_fee == 1.0
assert f.clearing_fee == 0.5
assert f.total_fee == 3.5

s = calc.calculate(symbol="SBER@MISX", asset_class="STOCK", qty=10, price=300, side="BUY")
assert s.total_fee == 1.8, s

print("FEE_CALCULATOR_OK")
PY
