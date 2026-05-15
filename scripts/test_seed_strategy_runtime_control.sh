#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/seed_strategy_runtime_control.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/seed_strategy_runtime_control.py").read_text(encoding="utf-8")

assert "OZON@MISX" in text
assert "TREND_PULLBACK_EQUITY" in text
assert "MEAN_REVERSION_EQUITY" in text
assert "seed_runtime_control_no_data" in text
assert "on conflict (symbol, strategy) do nothing" in text

print("OK: seed strategy_runtime_control script compile/static check")
PY
