#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export FUTURES_SPEC_BR_STEP_VALUE=10
export FUTURES_SPEC_NG_STEP_VALUE=7.43
export FUTURES_SPEC_SI_STEP_VALUE=1

python - <<'PY'
from finam_core.instruments.contract_specs import ContractSpecRegistry
from finam_core.analytics.futures_pnl import FuturesPnlCalculator

r = ContractSpecRegistry()
br = r.get("BRM6@RTSX")
ng = r.get("NGK6@RTSX")
si = r.get("SiM6@RTSX")

assert br.min_price_step == 0.01
assert br.step_value == 10.0
assert ng.min_price_step == 0.001
assert ng.step_value == 7.43
assert si.min_price_step == 1.0
assert si.step_value == 1.0

calc = FuturesPnlCalculator(r)

assert calc.pnl(symbol="BRM6@RTSX", side="BUY", entry=80.00, exit=80.35, qty=2) == 700.0
assert calc.pnl(symbol="BRM6@RTSX", side="SELL", entry=80.00, exit=79.50, qty=1) == 500.0
assert round(calc.pnl(symbol="NGK6@RTSX", side="BUY", entry=3.000, exit=3.010, qty=3), 2) == 222.9
assert calc.pnl(symbol="SiM6@RTSX", side="BUY", entry=93450, exit=93500, qty=1) == 50.0
assert calc.risk_money(symbol="BRM6@RTSX", entry=80.00, stop=79.50, qty=1) == 500.0

print("CONTRACT_SPECS_AND_FUTURES_PNL_OK")
PY
