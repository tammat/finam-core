#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/update_runtime_control_from_dynamic_universe.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/update_runtime_control_from_dynamic_universe.py").read_text(encoding="utf-8")

checks = [
    "strategy_runtime_control",
    "dynamic_watchlist",
    "runtime_control_seed_from_dynamic_universe",
    "risk_multiplier",
    "updated as",
    "where not exists",
    "is_active = true",
]

for c in checks:
    assert c in text, c

print("OK: runtime control dynamic universe feed static check")
PY

PYTHONPATH=src python src/scripts/update_runtime_control_from_dynamic_universe.py
