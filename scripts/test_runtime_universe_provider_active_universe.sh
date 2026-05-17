#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/data/runtime_universe_provider.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/data/runtime_universe_provider.py").read_text(encoding="utf-8")

assert "runtime_active_universe" in text
assert "dynamic_watchlist" in text
assert "strategy <> 'NO_TRADE'" in text
assert "active_symbols" in text

print("OK: RuntimeUniverseProvider uses runtime_active_universe with fallback")
PY
