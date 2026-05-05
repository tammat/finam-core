#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH=src

python -m py_compile src/finam_core/contracts/contract_resolver.py

BR_CONTRACT=BRM6@RTSX \
NG_CONTRACT=NGK6@RTSX \
USDRUB_CONTRACT=USDRUBF@RTSX \
python - <<'PY'
from finam_core.contracts.contract_resolver import ContractResolver

r = ContractResolver()

assert r.resolve("BR") == "BRM6@RTSX"
assert r.resolve("NG") == "NGK6@RTSX"
assert r.resolve("USDRUB") == "USDRUBF@RTSX"
assert r.next_contract("BR") == "BRN6@RTSX"
assert r.next_contract("NG") == "NGN6@RTSX"

print("CONTRACT_RESOLVER_TEST_OK")
PY
