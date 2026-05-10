#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/run_market_pipeline.py").read_text(encoding="utf-8")

assert "RecoveryOrchestrator" in text
assert "ENABLE_RECOVERY_ORCHESTRATOR" in text
assert "PIPE_RECOVERY_ORCHESTRATOR_OK" in text
assert "PIPE_RECOVERY_ORCHESTRATOR_BLOCK" in text
assert "raise SystemExit(2)" in text

print("PIPELINE_RECOVERY_ORCHESTRATOR_WIRING_OK")
PY
