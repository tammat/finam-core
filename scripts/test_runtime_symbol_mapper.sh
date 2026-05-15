#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.contracts.runtime_symbol_mapper import RuntimeSymbolMapper

cases = {
    "BRM6@RTSX": "BR_CONT",
    "BRN6@RTSX": "BR_CONT",
    "NGQ6@RTSX": "NG_CONT",
    "OZON@MISX": "OZON@MISX",
    "PLZL@MISX": "PLZL@MISX",
}

for symbol, expected in cases.items():
    actual = RuntimeSymbolMapper.runtime_symbol(symbol)

    assert actual == expected, (
        f"{symbol}: expected={expected} actual={actual}"
    )

print("OK: runtime symbol mapper")
PY
