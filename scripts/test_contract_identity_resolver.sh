#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/contracts/contract_identity_resolver.py

python - <<'PY'
from finam_core.contracts.contract_identity_resolver import ContractIdentityResolver

cases = {
    "BRM6@RTSX": ("BR", "BR_CONT", "M", "6", True),
    "BRN6@RTSX": ("BR", "BR_CONT", "N", "6", True),
    "NGH6@RTSX": ("NG", "NG_CONT", "H", "6", True),
    "NGK6@RTSX": ("NG", "NG_CONT", "K", "6", True),
    "USDRUBF@RTSX": ("USDRUB", "USDRUB_CONT", "F", "", True),
    "SBER@MISX": ("SBER", "SBER", None, None, False),
    "OZON@MISX": ("OZON", "OZON", None, None, False),
    "SFIN@MISX": ("SFIN", "SFIN", None, None, False),
}

for symbol, expected in cases.items():
    identity = ContractIdentityResolver.resolve(symbol)
    root, continuous, month_code, year_code, is_futures = expected

    print(
        symbol,
        "->",
        identity.root,
        identity.continuous,
        identity.month_code,
        identity.year_code,
        identity.is_futures,
    )

    assert identity.root == root
    assert identity.continuous == continuous
    assert identity.month_code == month_code
    assert identity.year_code == year_code
    assert identity.is_futures == is_futures

print("OK: ContractIdentityResolver works for BR/NG/USDRUB futures and stocks")
PY
