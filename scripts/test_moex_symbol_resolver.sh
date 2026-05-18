#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/data/moex_symbol_resolver.py

python - <<'PY'
from finam_core.data.moex_symbol_resolver import MoexSymbolResolver

r = MoexSymbolResolver()

sber = r.resolve("SBER@MISX")
assert sber.symbol == "SBER"
assert sber.engine == "stock"
assert sber.market == "shares"
assert sber.board == "TQBR"
assert sber.asset_class == "equity"

br = r.resolve("BRM6@RTSX")
assert br.symbol == "BRM6"
assert br.engine == "futures"
assert br.market == "forts"
assert br.board == "RFUD"
assert br.asset_class == "futures"

sber2 = r.resolve("SBER")
assert sber2.asset_class == "equity"

br2 = r.resolve("BRM6")
assert br2.asset_class == "futures"

ng = r.resolve("NGK6")
assert ng.asset_class == "futures"

print("OK: moex symbol resolver")
PY
