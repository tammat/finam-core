#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/scripts/seed_runtime_control_from_strategy_map.py \
  src/finam_core/contracts/runtime_symbol_mapper.py \
  src/finam_core/strategy/symbol_strategy_map.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/seed_runtime_control_from_strategy_map.py").read_text(encoding="utf-8")

assert "SYMBOL_STRATEGY_MAP" in text
assert "RuntimeSymbolMapper.runtime_symbol(raw_symbol)" in text
assert "on conflict (symbol, strategy) do nothing" in text

print("OK: runtime-control seed from strategy map script static check")
PY
