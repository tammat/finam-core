#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/data/moex_candle_provider.py

python - <<'PY'
from finam_core.data.moex_candle_provider import MoexCandleProvider

provider = MoexCandleProvider()
assert provider.INTERVALS["M5"] == 5
assert provider.INTERVALS["H1"] == 60

print("OK: moex candle provider compile")
PY
