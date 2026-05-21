#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.portfolio.position_symbol_normalizer import normalize_position_symbol

assert normalize_position_symbol("LKOH") == "LKOH@MISX"
assert normalize_position_symbol("SBERP") == "SBERP@MISX"
assert normalize_position_symbol("BRM6") == "BRM6@RTSX"
assert normalize_position_symbol("NGK6") == "NGK6@RTSX"
assert normalize_position_symbol("PLZL@MISX") == "PLZL@MISX"

print("TEST_POSITION_SYMBOL_NORMALIZER_OK")
PY
