#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/backfill_missing_strategy_attribution_from_map.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/backfill_missing_strategy_attribution_from_map.py").read_text(encoding="utf-8")

assert "SYMBOL_STRATEGY_MAP.get(symbol, DEFAULT_STRATEGY)" in text
assert "strategy_attribution_map_backfill_v1" in text
assert "continuous_symbol" in text
assert "confidence" in text

print("OK: missing strategy attribution map backfill static check")
PY
