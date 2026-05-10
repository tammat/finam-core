#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from pathlib import Path

p = Path("src/scripts/run_market_pipeline.py")

text = p.read_text(encoding="utf-8")

assert "StartupRecoveryGate(" in text
assert "STARTUP_RECOVERY_GATE_BLOCK" in text
assert "STARTUP_RECOVERY_GATE_OK" in text

print("RUN_MARKET_PIPELINE_STARTUP_GATE_OK")
PY
