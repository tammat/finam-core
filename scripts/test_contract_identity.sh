#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/market/contract_identity.py \
  src/finam_core/contracts/contract_identity_resolver.py

python - <<'PY'
from finam_core.market.contract_identity import ContractIdentityResolver

r = ContractIdentityResolver()

brm = r.resolve("BRM6@RTSX")
assert brm.root_symbol == "BR"
assert brm.continuous_symbol == "BR_CONT"
assert brm.contract_code == "M6"

brn = r.resolve("BRN6@RTSX")
assert brn.root_symbol == "BR"
assert brn.continuous_symbol == "BR_CONT"
assert brn.contract_code == "N6"

ng = r.resolve("NGH6@RTSX")
assert ng.root_symbol == "NG"
assert ng.continuous_symbol == "NG_CONT"
assert ng.contract_code == "H6"

sber = r.resolve("SBER@MISX")
assert sber.root_symbol == "SBER"
assert sber.continuous_symbol == "SBER@MISX"
assert sber.contract_code is None

print("OK: market contract identity wrapper uses canonical resolver")
PY
