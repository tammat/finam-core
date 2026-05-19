#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_market_radar.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_market_radar.py").read_text(encoding="utf-8")

checks = [
    "moex_liquid_universe",
    "PIPE_LIQUID_UNIVERSE",
    "PIPE_LIQUID_UNIVERSE_FILTERED",
    "--use-liquid-universe",
    "PostgresLogger",
]

for c in checks:
    assert c in text, c

print("OK: market radar uses liquid universe")
PY
