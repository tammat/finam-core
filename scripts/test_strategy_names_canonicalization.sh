#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/common/strategy_names.py

python - <<'PY'
from finam_core.common.strategy_names import normalize_strategy_name

assert normalize_strategy_name("br_conservative_breakout") == "BR_CONSERVATIVE_BREAKOUT"
assert normalize_strategy_name("BR_CONSERVATIVE_BREAKOUT") == "BR_CONSERVATIVE_BREAKOUT"
assert normalize_strategy_name(" unknown ") == "unknown"
assert normalize_strategy_name(None) == ""

print("STRATEGY_NAMES_CANONICALIZATION_TEST_OK")
PY
